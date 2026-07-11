from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from src.utils.logger import logger
from src.utils.exceptions import AppException
import time

# Paths that do NOT require authentication
PUBLIC_PATHS = {
    "/api/health",
    "/api",
    "/docs",
    "/openapi.json",
    "/redoc",
}


async def get_user_id_from_request(request: Request) -> str:
    """Extract user ID from request headers or session.
    
    In production, this would verify a JWT token from the Authorization header.
    For development, falls back to a header or query param.
    """
    # Try Authorization header (Bearer token from NextAuth JWT)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # In development, decode a simple user ID from token
        # In production, verify the JWT with NextAuth's secret
        try:
            from jose import jwt
            payload = jwt.decode(token, "development-secret", algorithms=["HS256"])
            return payload.get("sub", "default")
        except Exception:
            pass

    # Fallback: X-User-Id header (for development/testing)
    user_id = request.headers.get("X-User-Id", "")
    if user_id:
        return user_id

    # Last resort: query param
    user_id = request.query_params.get("user_id", "")
    if user_id:
        return user_id

    return "default"


async def error_handler_middleware(request: Request, call_next):
    try:
        start_time = time.time()
        response = await call_next(request)
        elapsed = time.time() - start_time
        response.headers["X-Process-Time"] = str(elapsed)
        return response
    except AppException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.message},
        )
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error"},
        )


async def cors_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response
