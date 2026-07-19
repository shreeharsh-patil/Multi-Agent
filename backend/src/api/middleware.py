from fastapi import Request, HTTPException
import json
from fastapi.responses import JSONResponse, Response
from src.config import settings
from src.utils.logger import logger
from src.utils.exceptions import AppException
from src.services.auth.service import verify_access_token
import time

# Paths that do NOT require authentication
PUBLIC_PATHS = {
    "/api/health",
    "/api",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/auth/login",
}

# Prefixes that are public only for specific HTTP methods. The shared-chat
# read view (GET) must stay open, but creating/revoking a share (POST/DELETE)
# requires an authenticated user so request.state.user is populated.
PUBLIC_METHOD_PREFIXES = (
    ("GET", "/api/shares/chat/"),
    ("POST", "/api/voice/"),
)

# Suffixes for GET routes the browser opens directly (<img src>, download/export
# links) with no Authorization header, so they cannot be user-scoped and must
# stay public regardless of the (dynamic) id in the middle of the path.
PUBLIC_GET_SUFFIXES = (
    "/download",
    "/download/content",
)


def _is_public(method: str, path: str) -> bool:
    # PUBLIC_PATHS are matched exactly. Using a prefix match here would be a
    # security hole: "/api" would make every "/api/..." route public and stop
    # jwt_auth_middleware from ever setting request.state.user.
    if path in PUBLIC_PATHS:
        return True
    if any(method == m and path.startswith(p) for m, p in PUBLIC_METHOD_PREFIXES):
        return True
    if method == "GET" and path.startswith("/api/") and any(path.endswith(s) for s in PUBLIC_GET_SUFFIXES):
        return True
    return False


def resolve_user_id(request: Request, fallback: str = "default") -> str:
    """Resolve the authenticated user id set by ``jwt_auth_middleware``.

    Routes should use this instead of trusting a body/query ``user_id`` so that
    persisted records (notes, research, plans, search history) are scoped to the
    signed-in user rather than the shared ``"default"`` bucket.
    """
    user = getattr(request.state, "user", None)
    if user and user.get("sub"):
        return user["sub"]
    return fallback


async def get_user_id_from_request(request: Request) -> str:
    """Extract user ID from request.

    Priority:
    1. JWT from Authorization header (production)
    2. X-User-Id header (development/testing)
    3. user_id query param (development/testing)
    4. Default fallback
    """
    # 1. JWT Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        payload = verify_access_token(token)
        if payload and payload.get("sub"):
            return payload["sub"]

    # 2. X-User-Id header (for development/testing)
    user_id = request.headers.get("X-User-Id", "")
    if user_id:
        return user_id

    # 3. Query param fallback
    user_id = request.query_params.get("user_id", "")
    if user_id:
        return user_id

    return "default"


async def jwt_auth_middleware(request: Request, call_next):
    """Verify JWT on protected routes and set request.state.user.

    Public paths are allowed through without authentication.
    For protected paths, the Authorization header is checked.
    In development mode (settings.debug=True), falls back to
    X-User-Id header or user_id query param if no JWT is provided.
    """
    path = request.url.path

    # Skip auth for public paths
    if _is_public(request.method, path):
        return await call_next(request)

    # Skip auth for OPTIONS (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)

    # Try to authenticate via JWT
    auth_header = request.headers.get("Authorization", "")
    user_payload = None

    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        user_payload = verify_access_token(token)

    if user_payload:
        # Authenticated via JWT
        request.state.user = user_payload

        # Capture and persist Google OAuth access token to database so ADK agent tools can access it.
        google_token = request.headers.get("X-Google-Access-Token") or request.headers.get("X-Drive-Access-Token")
        if google_token and user_payload.get("sub"):
            try:
                from beanie import PydanticObjectId
                from src.models.user import User
                user_id = user_payload["sub"]
                PydanticObjectId(user_id)
                user = await User.get(user_id)
                if user and user.access_token != google_token:
                    user.access_token = google_token
                    await user.save()
                    logger.info(f"Updated Google access token in database for user: {user.email}")
            except Exception:
                pass

        return await call_next(request)

    # Development fallback: allow X-User-Id header or user_id query param
    if settings.debug:
        user_id = request.headers.get("X-User-Id", "")
        if not user_id:
            user_id = request.query_params.get("user_id", "")
        if user_id:
            request.state.user = {"sub": user_id, "email": "dev@localhost", "name": "Developer"}

            google_token = request.headers.get("X-Google-Access-Token") or request.headers.get("X-Drive-Access-Token")
            if google_token:
                try:
                    from beanie import PydanticObjectId
                    from src.models.user import User
                    PydanticObjectId(user_id)
                    user = await User.get(user_id)
                    if user and user.access_token != google_token:
                        user.access_token = google_token
                        await user.save()
                except Exception:
                    pass

            return await call_next(request)
        # Even in dev mode, if there's absolutely no user context, use "default"
        # so existing routes don't break
        request.state.user = {"sub": "default", "email": "", "name": "Default User"}
        return await call_next(request)

    # Production: reject unauthenticated requests
    return JSONResponse(
        status_code=401,
        content={"success": False, "error": "Authentication required. Provide a Bearer token in the Authorization header."},
        headers=_cors_headers(request),
    )


def _cors_headers(request: Request) -> dict:
    origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    origin = request.headers.get("origin", "")
    if origin in origins or "*" in origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    return {}


async def error_handler_middleware(request: Request, call_next):
    try:
        start_time = time.time()
        response = await call_next(request)
        elapsed = time.time() - start_time
        response.headers["X-Process-Time"] = str(elapsed)
        return response
    except HTTPException:
        raise  # Let FastAPI/Starlette handle HTTPException properly (preserves status code)
    except AppException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.message},
            headers=_cors_headers(request),
        )
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error"},
            headers=_cors_headers(request),
        )


async def api_response_envelope_middleware(request: Request, call_next):
    """Normalize successful JSON API responses for the frontend client.

    The frontend uses a single ``{success, data, error}`` contract, while
    several older routes returned raw lists or objects.  Normalize only JSON
    responses under /api; streaming and file responses must remain untouched.
    """
    response = await call_next(request)
    if not request.url.path.startswith("/api"):
        return response

    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type or "text/event-stream" in content_type:
        return response

    body = getattr(response, "body", None)
    if body is None:
        # BaseHTTPMiddleware commonly exposes the response through an async
        # body iterator instead of a populated ``body`` attribute.
        body_iterator = getattr(response, "body_iterator", None)
        if body_iterator is None:
            return response
        chunks = []
        async for chunk in body_iterator:
            chunks.append(chunk)
        body = b"".join(chunks)

    try:
        payload = json.loads(body)
    except (TypeError, ValueError):
        return response

    # Build a new JSONResponse with the original status and headers so the
    # response body is not consumed in-place (which would leave the client
    # with an empty response when the original response is returned directly).
    headers = dict(response.headers)
    headers.pop("content-length", None)

    # Error responses are already in the public contract.  Successful
    # responses are wrapped, including ChatResponse/Auth responses whose
    # payloads contain their own domain fields.
    if response.status_code >= 400:
        if isinstance(payload, dict) and "success" in payload:
            return JSONResponse(
                status_code=response.status_code,
                content=payload,
                headers=headers,
            )
        error = payload.get("detail", payload) if isinstance(payload, dict) else payload
        return JSONResponse(
            status_code=response.status_code,
            content={"success": False, "error": error},
            headers=headers,
        )

    if isinstance(payload, dict) and set(payload) >= {"success", "data"}:
        return JSONResponse(
            status_code=response.status_code,
            content=payload,
            headers=headers,
        )

    return JSONResponse(
        status_code=response.status_code,
        content={"success": True, "data": payload},
        headers=headers,
    )
