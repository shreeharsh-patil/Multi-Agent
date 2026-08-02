import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.middleware import resolve_user_id
from src.models.flashcard import Flashcard, FlashcardDeck, FlashcardReview
from src.services.flashcards import schedule_review
from src.services.llm import llm_service


router = APIRouter(prefix="/api/flashcards", tags=["Flashcards"])


class DeckInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    workspace_id: str | None = None


class CardInput(BaseModel):
    front: str = Field(min_length=1, max_length=4000)
    back: str = Field(min_length=1, max_length=8000)
    tags: list[str] = Field(default_factory=list)


class ReviewInput(BaseModel):
    rating: Literal["again", "hard", "good", "easy"]


class GenerateInput(BaseModel):
    deck_id: str
    source: str = Field(min_length=10, max_length=30000)
    count: int = Field(default=10, ge=1, le=30)


def serialize_card(card: Flashcard) -> dict:
    return {
        "id": str(card.id), "deckId": card.deck_id, "front": card.front, "back": card.back,
        "tags": card.tags, "easeFactor": card.ease_factor, "intervalDays": card.interval_days,
        "repetitions": card.repetitions, "lapses": card.lapses,
        "dueAt": card.due_at.isoformat(), "lastReviewedAt": card.last_reviewed_at.isoformat() if card.last_reviewed_at else None,
    }


def generated_card_values(value: object) -> tuple[str, str, list[str]] | None:
    """Accept the common field names returned by flashcard prompts/models."""
    if not isinstance(value, dict):
        return None
    front = value.get("front") or value.get("question") or value.get("prompt") or value.get("term")
    back = value.get("back") or value.get("answer") or value.get("response") or value.get("definition")
    if not front or not back:
        return None
    raw_tags = value.get("tags", [])
    tags = raw_tags if isinstance(raw_tags, list) else [raw_tags]
    return str(front)[:4000], str(back)[:8000], [str(tag)[:50] for tag in tags[:10]]


async def owned_deck(deck_id: str, user_id: str) -> FlashcardDeck:
    deck = await FlashcardDeck.get(deck_id)
    if not deck or (deck.user_id != user_id and deck.user_id != "default" and user_id != "default"):
        raise HTTPException(404, "Deck not found")
    return deck


@router.get("/decks")
async def list_decks(request: Request) -> list[dict]:
    user_id = resolve_user_id(request)
    decks = await FlashcardDeck.find(FlashcardDeck.user_id == user_id).sort(-FlashcardDeck.updated_at).to_list()
    cards = await Flashcard.find(Flashcard.user_id == user_id).to_list()
    now = datetime.now(timezone.utc)
    stats: dict[str, dict[str, int]] = {}
    for card in cards:
        values = stats.setdefault(card.deck_id, {"cardCount": 0, "dueCount": 0})
        values["cardCount"] += 1
        if card.due_at <= now:
            values["dueCount"] += 1
    return [{
        "id": str(deck.id), "name": deck.name, "description": deck.description,
        "workspaceId": deck.workspace_id, "createdAt": deck.created_at.isoformat(),
        **stats.get(str(deck.id), {"cardCount": 0, "dueCount": 0}),
    } for deck in decks]


@router.post("/decks")
async def create_deck(request: Request, body: DeckInput) -> dict:
    deck = FlashcardDeck(user_id=resolve_user_id(request), **body.model_dump())
    await deck.insert()
    return {"id": str(deck.id), "name": deck.name, "description": deck.description, "cardCount": 0, "dueCount": 0}


@router.delete("/decks/{deck_id}")
async def delete_deck(deck_id: str, request: Request) -> dict:
    user_id = resolve_user_id(request)
    deck = await owned_deck(deck_id, user_id)
    await Flashcard.find(Flashcard.user_id == user_id, Flashcard.deck_id == deck_id).delete()
    await FlashcardReview.find(FlashcardReview.user_id == user_id, FlashcardReview.deck_id == deck_id).delete()
    await deck.delete()
    return {"deleted": True}


@router.get("/decks/{deck_id}/cards")
async def list_cards(deck_id: str, request: Request) -> list[dict]:
    user_id = resolve_user_id(request)
    await owned_deck(deck_id, user_id)
    cards = await Flashcard.find(Flashcard.user_id == user_id, Flashcard.deck_id == deck_id).sort(Flashcard.due_at).to_list()
    return [serialize_card(card) for card in cards]


@router.post("/decks/{deck_id}/cards")
async def create_card(deck_id: str, request: Request, body: CardInput) -> dict:
    user_id = resolve_user_id(request)
    deck = await owned_deck(deck_id, user_id)
    card = Flashcard(user_id=user_id, deck_id=deck_id, front=body.front.strip(), back=body.back.strip(), tags=body.tags[:20])
    await card.insert()
    deck.updated_at = datetime.now(timezone.utc)
    await deck.save()
    return serialize_card(card)


@router.delete("/cards/{card_id}")
async def delete_card(card_id: str, request: Request) -> dict:
    user_id = resolve_user_id(request)
    card = await Flashcard.get(card_id)
    if not card or card.user_id != user_id:
        raise HTTPException(404, "Card not found")
    await card.delete()
    return {"deleted": True}


@router.get("/due")
async def due_cards(request: Request, deck_id: str | None = None, limit: int = 50) -> list[dict]:
    user_id = resolve_user_id(request)
    filters = [Flashcard.user_id == user_id, Flashcard.due_at <= datetime.now(timezone.utc)]
    if deck_id:
        await owned_deck(deck_id, user_id)
        filters.append(Flashcard.deck_id == deck_id)
    cards = await Flashcard.find(*filters).sort(Flashcard.due_at).limit(min(max(limit, 1), 100)).to_list()
    return [serialize_card(card) for card in cards]


@router.post("/cards/{card_id}/review")
async def review_card(card_id: str, request: Request, body: ReviewInput) -> dict:
    user_id = resolve_user_id(request)
    card = await Flashcard.get(card_id)
    if not card or card.user_id != user_id:
        raise HTTPException(404, "Card not found")
    now = datetime.now(timezone.utc)
    previous_interval = card.interval_days
    result = schedule_review(card, body.rating, now)
    card.ease_factor = result.ease_factor
    card.interval_days = result.interval_days
    card.repetitions = result.repetitions
    card.lapses = result.lapses
    card.due_at = result.due_at
    card.last_reviewed_at = now
    card.updated_at = now
    await card.save()
    await FlashcardReview(
        user_id=user_id, card_id=card_id, deck_id=card.deck_id, rating=body.rating,
        previous_interval_days=previous_interval, next_interval_days=result.interval_days,
        reviewed_at=now, next_due_at=result.due_at,
    ).insert()
    return serialize_card(card)


@router.post("/generate")
async def generate_cards(request: Request, body: GenerateInput) -> dict:
    user_id = resolve_user_id(request)
    deck = await owned_deck(body.deck_id, user_id)
    prompt = (
        f"Create exactly {body.count} concise study flashcards from the source below. "
        "Test one fact or concept per card. Return JSON only as "
        "{\"cards\":[{\"front\":\"question\",\"back\":\"answer\",\"tags\":[\"topic\"]}]}.\n\n"
        f"SOURCE:\n{body.source}"
    )
    output = await llm_service.generate(prompt, temperature=0.3, max_output_tokens=6000)
    try:
        start, end = output.index("{"), output.rindex("}") + 1
        payload = json.loads(output[start:end])
        values = payload.get("cards", []) if isinstance(payload, dict) else payload
        if not isinstance(values, list):
            raise ValueError("cards must be an array")
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "The agent returned invalid flashcard data") from exc
    created = []
    for value in values[:body.count]:
        normalized = generated_card_values(value)
        if not normalized:
            continue
        front, back, tags = normalized
        card = Flashcard(user_id=user_id, deck_id=body.deck_id, front=front, back=back, tags=tags)
        await card.insert()
        created.append(serialize_card(card))
    if not created:
        raise HTTPException(502, "The agent did not return any usable flashcards")
    deck.updated_at = datetime.now(timezone.utc)
    await deck.save()
    return {"created": len(created), "cards": created}
