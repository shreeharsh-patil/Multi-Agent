from fastapi import Request
from fastapi.responses import JSONResponse
from src.utils.logger import logger
from src.utils.exceptions import AppException
import time


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
