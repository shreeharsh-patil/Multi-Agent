"""Content Extractor and Passage Ranker Engine for Google ADK.

Prevents sending entire 30,000-token websites into Gemini.
Decomposes clean website text into discrete section chunks and selects only the top relevant passages
while strictly preserving complete citation provenance (source_id, url, title, heading, text, page, retrieval_timestamp).
"""

from __future__ import annotations

import datetime
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.utils.logger import logger


@dataclass
class PassageChunk:
    """A distinct extracted passage with full citation provenance."""
    source_id: str
    url: str
    title: str
    heading: str
    text: str
    page: Optional[int] = None
    retrieval_timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    relevance_score: float = 0.0
    rank_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "heading": self.heading,
            "text": self.text,
            "page": self.page,
            "retrieval_timestamp": self.retrieval_timestamp,
            "relevance_score": round(self.relevance_score, 3),
            "rank_reason": self.rank_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PassageChunk:
        return cls(
            source_id=data.get("source_id", ""),
            url=data.get("url", ""),
            title=data.get("title", ""),
            heading=data.get("heading", ""),
            text=data.get("text", ""),
            page=data.get("page"),
            retrieval_timestamp=data.get("retrieval_timestamp", ""),
            relevance_score=data.get("relevance_score", 0.0),
            rank_reason=data.get("rank_reason", ""),
        )


@dataclass
class ExtractedPassagesPacket:
    """Container of ranked passages ready for evidence verification."""
    query: str
    total_chunks_extracted: int
    selected_passages: list[PassageChunk] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "total_chunks_extracted": self.total_chunks_extracted,
            "selected_passages": [p.to_dict() for p in self.selected_passages],
        }


class ContentExtractorEngine:
    """Splits full page text/documentation into structured section chunks based on headings and paragraphs."""

    @classmethod
    def generate_source_id(cls, url: str, index: int = 0) -> str:
        """Generate a deterministic, clean source ID."""
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:6]
        return f"src_{url_hash}_{index + 1}"

    @classmethod
    def split_into_sections(
        cls,
        text: str,
        url: str,
        title: str = "Web Document",
        source_id: Optional[str] = None,
        page: Optional[int] = None,
        retrieval_timestamp: Optional[str] = None,
        max_chunk_chars: int = 1500,
    ) -> list[PassageChunk]:
        """Split clean webpage text into heading-anchored chunks while retaining full citation metadata."""
        if not text or not text.strip():
            return []

        timestamp = retrieval_timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        chunks: list[PassageChunk] = []

        # Split by markdown headers (#, ##, ###, ####) or section breaks
        heading_pattern = re.compile(r"(?m)^(#{1,4}\s+.+)$")
        parts = heading_pattern.split(text)

        current_heading = "Introduction / Overview"
        section_idx = 0

        i = 0
        while i < len(parts):
            part = parts[i].strip()
            if not part:
                i += 1
                continue

            if part.startswith("#"):
                current_heading = re.sub(r"^#+\s*", "", part).strip()
                i += 1
                if i < len(parts):
                    content = parts[i].strip()
                else:
                    content = ""
            else:
                content = part

            if content:
                # If content exceeds max_chunk_chars, split by double newlines or paragraphs
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                buffer = ""
                
                for p in paragraphs:
                    if len(buffer) + len(p) < max_chunk_chars:
                        buffer = f"{buffer}\n\n{p}".strip() if buffer else p
                    else:
                        if buffer:
                            chunks.append(PassageChunk(
                                source_id=cls.generate_source_id(url, len(chunks)),
                                url=url,
                                title=title,
                                heading=current_heading,
                                text=buffer,
                                page=page,
                                retrieval_timestamp=timestamp,
                            ))
                        buffer = p

                if buffer:
                    chunks.append(PassageChunk(
                        source_id=cls.generate_source_id(url, len(chunks)),
                        url=url,
                        title=title,
                        heading=current_heading,
                        text=buffer,
                        page=page,
                        retrieval_timestamp=timestamp,
                    ))

            i += 1

        # Fallback if no markdown headings existed
        if not chunks and text:
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            buffer = ""
            for p in paragraphs:
                if len(buffer) + len(p) < max_chunk_chars:
                    buffer = f"{buffer}\n\n{p}".strip() if buffer else p
                else:
                    if buffer:
                        chunks.append(PassageChunk(
                            source_id=cls.generate_source_id(url, len(chunks)),
                            url=url,
                            title=title,
                            heading="Document Body",
                            text=buffer,
                            page=page,
                            retrieval_timestamp=timestamp,
                        ))
                    buffer = p
            if buffer:
                chunks.append(PassageChunk(
                    source_id=cls.generate_source_id(url, len(chunks)),
                    url=url,
                    title=title,
                    heading="Document Body",
                    text=buffer,
                    page=page,
                    retrieval_timestamp=timestamp,
                ))

        logger.info(f"ContentExtractor split URL '{url}' ({len(text)} chars) into {len(chunks)} passage chunks")
        return chunks


class PassageRankerEngine:
    """Ranks passage chunks by relevance to the user's specific query and selects top passages."""

    @classmethod
    def compute_passage_relevance(cls, query: str, passage: PassageChunk) -> float:
        """Compute keyword and semantic overlap score between query and passage chunk."""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        if not q_tokens:
            return 0.5

        stop_words = {"what", "is", "the", "latest", "recent", "for", "and", "in", "of", "to", "a", "an", "how", "why"}
        key_tokens = q_tokens - stop_words or q_tokens

        text_to_search = f"{passage.heading.lower()} {passage.text.lower()}"
        matches = sum(1 for tok in key_tokens if tok in text_to_search)
        overlap_score = matches / len(key_tokens)

        # Boost if heading matches query terms
        heading_matches = sum(1 for tok in key_tokens if tok in passage.heading.lower())
        heading_boost = 0.25 if heading_matches > 0 else 0.0

        # Exact phrase bonus
        phrase_boost = 0.2 if query.lower().strip() in text_to_search else 0.0

        return min(1.0, (overlap_score * 0.6) + heading_boost + phrase_boost)

    @classmethod
    def rank_and_select(
        cls,
        query: str,
        passages: list[PassageChunk],
        top_k: int = 5,
    ) -> ExtractedPassagesPacket:
        """Rank passage chunks and select only the top K most relevant passages without losing citation provenance."""
        if not passages:
            return ExtractedPassagesPacket(
                query=query,
                total_chunks_extracted=0,
                selected_passages=[],
            )

        scored_passages: list[PassageChunk] = []
        for p in passages:
            score = cls.compute_passage_relevance(query, p)
            p.relevance_score = score
            if score >= 0.7:
                p.rank_reason = f"Strong semantic alignment with '{query[:30]}' in section '{p.heading}'"
            elif score >= 0.4:
                p.rank_reason = f"Moderate keyword relevance in section '{p.heading}'"
            else:
                p.rank_reason = f"Contextual background match in section '{p.heading}'"
            scored_passages.append(p)

        # Sort descending by relevance score
        scored_passages.sort(key=lambda x: x.relevance_score, reverse=True)

        selected = scored_passages[:top_k]
        logger.info(
            f"PassageRanker filtered {len(passages)} total chunks down to top {len(selected)} relevant passages for '{query[:50]}'"
        )

        return ExtractedPassagesPacket(
            query=query,
            total_chunks_extracted=len(passages),
            selected_passages=selected,
        )
