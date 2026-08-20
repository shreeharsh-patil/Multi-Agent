"""Authentication and user management API routes."""

from datetime import datetime, timezone
from typing import Optional

import httpx

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from beanie import PydanticObjectId

from src.models.user import User
from src.config import settings
from src.services.auth.service import create_access_token, verify_access_token
from src.utils.logger import logger

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ── Request / Response Models ──────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str
    name: str
    image: Optional[str] = None
    google_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


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


async def _verify_google_identity(access_token: str) -> dict:
    """Validate an OAuth token server-side before trusting identity fields.

    The frontend session is useful for the browser, but it is not proof to the
    API that a caller owns an arbitrary email address. Google userinfo binds
    the supplied token to the identity we persist and sign into a backend JWT.
    """
    if not access_token:
        raise HTTPException(status_code=401, detail="Google authentication token is required")
    try:
        timeout = httpx.Timeout(settings.oauth_verification_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.TimeoutException as exc:
        logger.warning("Google identity verification timed out")
        raise HTTPException(status_code=503, detail="Google identity verification timed out") from exc
    except httpx.HTTPError as exc:
        logger.warning("Google identity verification failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Google identity verification is unavailable") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Google authentication token is invalid or expired")
    try:
        identity = response.json()
    except ValueError as exc:
        logger.warning("Google identity verification returned invalid JSON")
        raise HTTPException(status_code=503, detail="Google identity verification is unavailable") from exc
    if not identity.get("email") or identity.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="Google account email is not verified")
    return identity


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """Authenticate (or create) a user and return a JWT access token.

    Called by the frontend after a successful Google OAuth sign-in via NextAuth.
    Creates a new user in MongoDB if one doesn't already exist for this email.
    """
    # Production must never accept a caller-supplied email as proof of
    # identity. A development-only login remains available for local work.
    if settings.debug and not body.access_token:
        verified_email = body.email.strip().casefold()
        verified_name = body.name.strip() or verified_email
        verified_google_id = body.google_id
    else:
        identity = await _verify_google_identity(body.access_token or "")
        verified_email = str(identity["email"]).strip().casefold()
        if verified_email != body.email.strip().casefold():
            raise HTTPException(status_code=401, detail="Google identity does not match the requested email")
        verified_name = str(identity.get("name") or body.name).strip() or verified_email
        verified_google_id = str(identity.get("sub") or body.google_id or "") or None

    # Look up existing user using the verified identity.
    user = await User.find_one(User.email == verified_email)

    if not user:
        # Create new user
        user = User(
            email=verified_email,
            name=verified_name,
            avatar=body.image if settings.debug else identity.get("picture"),
            google_id=verified_google_id,
            access_token=body.access_token,
            refresh_token=body.refresh_token,
        )
        await user.insert()
        logger.info("Created new user: %s (%s)", user.email, user.id)
    else:
        # Update profile fields that may have changed
        needs_save = False
        if user.name != verified_name:
            user.name = verified_name
            needs_save = True
        verified_avatar = body.image if settings.debug else identity.get("picture")
        if verified_avatar and user.avatar != verified_avatar:
            user.avatar = verified_avatar
            needs_save = True
        if verified_google_id and user.google_id != verified_google_id:
            user.google_id = verified_google_id
            needs_save = True
        if body.access_token and user.access_token != body.access_token:
            user.access_token = body.access_token
            needs_save = True
        if body.refresh_token and user.refresh_token != body.refresh_token:
            user.refresh_token = body.refresh_token
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

    # A stale token can contain an ID from a previous database/environment.
    # Return a recoverable 404 instead of allowing Beanie to raise a 500.
    if not PydanticObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="User not found")

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
