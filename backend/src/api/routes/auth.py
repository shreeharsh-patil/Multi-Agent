"""Authentication and user management API routes."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.models.user import User
from src.services.auth.service import create_access_token, verify_access_token
from src.utils.logger import logger

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ── Request / Response Models ──────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str
    name: str
    image: Optional[str] = None
    google_id: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar: Optional[str] = None
    is_active: bool
    createdAt: str
    updatedAt: str
    preferences: dict


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    preferences: Optional[dict] = None


# ── Dependency: get current user from JWT ──────────────────────────────


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency that extracts the authenticated user from the JWT.

    Relies on the JWT auth middleware having set ``request.state.user``.
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── Routes ─────────────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """Authenticate (or create) a user and return a JWT access token.

    Called by the frontend after a successful Google OAuth sign-in via NextAuth.
    Creates a new user in MongoDB if one doesn't already exist for this email.
    """
    # Look up existing user
    user = await User.find_one(User.email == body.email)

    if not user:
        # Create new user
        user = User(
            email=body.email,
            name=body.name,
            avatar=body.image,
            google_id=body.google_id,
        )
        await user.insert()
        logger.info(f"Created new user: {body.email} ({user.id})")
    else:
        # Update profile fields that may have changed
        needs_save = False
        if body.name and user.name != body.name:
            user.name = body.name
            needs_save = True
        if body.image and user.avatar != body.image:
            user.avatar = body.image
            needs_save = True
        if body.google_id and user.google_id != body.google_id:
            user.google_id = body.google_id
            needs_save = True
        if needs_save:
            user.updated_at = datetime.now(timezone.utc)
            await user.save()

    # Sign JWT
    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        name=user.name,
    )

    return LoginResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "avatar": user.avatar,
        },
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: dict = Depends(get_current_user)) -> UserProfileResponse:
    """Return the profile of the currently authenticated user."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar=user.avatar,
        is_active=user.is_active,
        createdAt=user.created_at.isoformat(),
        updatedAt=user.updated_at.isoformat(),
        preferences={
            "theme": user.preferences.theme,
            "defaultModel": user.preferences.default_model,
            "notifications": user.preferences.notifications,
            "language": user.preferences.language,
            "useOpendocumentsRag": getattr(user.preferences, "use_opendocuments_rag", False),
            "memoryEnabled": getattr(user.preferences, "memory_enabled", True),
            "memoryAutoExtract": getattr(user.preferences, "memory_auto_extract", True),
        },
    )


@router.put("/me", response_model=UserProfileResponse)
async def update_me(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> UserProfileResponse:
    """Update the profile or preferences of the currently authenticated user."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    needs_save = False

    if body.name is not None and user.name != body.name:
        user.name = body.name
        needs_save = True
    if body.avatar is not None and user.avatar != body.avatar:
        user.avatar = body.avatar
        needs_save = True

    if body.preferences is not None:
        pref = body.preferences
        if "theme" in pref and user.preferences.theme != pref["theme"]:
            user.preferences.theme = pref["theme"]
            needs_save = True
        if "defaultModel" in pref and user.preferences.default_model != pref["defaultModel"]:
            user.preferences.default_model = pref["defaultModel"]
            needs_save = True
        if "notifications" in pref and user.preferences.notifications != pref["notifications"]:
            user.preferences.notifications = pref["notifications"]
            needs_save = True
        if "language" in pref and user.preferences.language != pref["language"]:
            user.preferences.language = pref["language"]
            needs_save = True
        if "useOpendocumentsRag" in pref and getattr(user.preferences, "use_opendocuments_rag", False) != pref["useOpendocumentsRag"]:
            user.preferences.use_opendocuments_rag = pref["useOpendocumentsRag"]
            needs_save = True
        if "memoryEnabled" in pref and getattr(user.preferences, "memory_enabled", True) != pref["memoryEnabled"]:
            user.preferences.memory_enabled = pref["memoryEnabled"]
            needs_save = True
        if "memoryAutoExtract" in pref and getattr(user.preferences, "memory_auto_extract", True) != pref["memoryAutoExtract"]:
            user.preferences.memory_auto_extract = pref["memoryAutoExtract"]
            needs_save = True

    if needs_save:
        user.updated_at = datetime.now(timezone.utc)
        await user.save()

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar=user.avatar,
        is_active=user.is_active,
        createdAt=user.created_at.isoformat(),
        updatedAt=user.updated_at.isoformat(),
        preferences={
            "theme": user.preferences.theme,
            "defaultModel": user.preferences.default_model,
            "notifications": user.preferences.notifications,
            "language": user.preferences.language,
            "useOpendocumentsRag": getattr(user.preferences, "use_opendocuments_rag", False),
            "memoryEnabled": getattr(user.preferences, "memory_enabled", True),
            "memoryAutoExtract": getattr(user.preferences, "memory_auto_extract", True),
        },
    )
