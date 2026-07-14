"""JWT authentication service.

Handles creating and verifying JSON Web Tokens for API authentication.
Uses python-jose (with cryptography) for JWT operations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from src.config import settings
from src.utils.logger import logger


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def create_access_token(
    user_id: str,
    email: str,
    name: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token for the given user.

    Args:
        user_id: The user's MongoDB document ID.
        email: User's email address.
        name: User's display name.
        expires_delta: Optional custom expiry; defaults to 24 hours.

    Returns:
        A signed JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def verify_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT access token.

    Args:
        token: The JWT string to verify.

    Returns:
        The decoded payload dict on success, or None if the token
        is expired, malformed, or signed with a different key.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None
