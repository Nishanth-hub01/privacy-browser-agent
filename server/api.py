import sys
from pathlib import Path

# Ensure both server/ and workspace root are in sys.path
SERVER_DIR = Path(__file__).resolve().parent
ROOT_DIR = SERVER_DIR.parent
for p in (str(ROOT_DIR), str(SERVER_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import uvicorn

try:
    from server.routes import router
    from server.schemas import ErrorResponse, ErrorDetail, ErrorCode
except ModuleNotFoundError:
    from routes import router
    from schemas import ErrorResponse, ErrorDetail, ErrorCode

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("server")

app = FastAPI(
    title="Privacy-Preserving Vision Browser Agent Server",
    version="1.0.0",
    description="FastAPI backend for analyzing sanitized browser context and planning actions.",
)

# Enable CORS for browser extension and local client communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_request_id_safely(request: Request) -> str:
    """Safely extracts request_id from cached request body or state without hanging.

    In Starlette/FastAPI, calling `await request.json()` in an exception handler after
    the body stream has already been consumed will block indefinitely. We safely inspect
    already-cached attributes or fall back to 'unknown'.
    """
    try:
        if hasattr(request, "_json") and isinstance(request._json, dict):
            return request._json.get("request_id", "unknown") or "unknown"
        if hasattr(request, "_body") and request._body:
            import json
            data = json.loads(request._body)
            if isinstance(data, dict):
                return data.get("request_id", "unknown") or "unknown"
    except Exception:
        pass
    return "unknown"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Returns INVALID_REQUEST for Pydantic schema failures."""
    request_id = _extract_request_id_safely(request)
    logger.warning("INVALID_REQUEST [%s]: %s", request_id, exc)
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            request_id=request_id,
            status="error",
            error=ErrorDetail(
                code=ErrorCode.INVALID_REQUEST,
                message=f"Request validation failed: {exc.errors()}",
            ),
        ).model_dump(),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Converts Starlette HTTP errors (404, 405, etc.) to the contract's JSON format."""
    request_id = _extract_request_id_safely(request)
    code = ErrorCode.INVALID_REQUEST if exc.status_code < 500 else ErrorCode.SERVER_ERROR
    logger.warning("HTTP %s [%s]: %s", exc.status_code, request_id, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            request_id=request_id,
            status="error",
            error=ErrorDetail(
                code=code,
                message=str(exc.detail),
            ),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for any unhandled exception — returns SERVER_ERROR in contract format.

    Prevents raw stack traces or HTML error pages from leaking to clients.
    """
    request_id = _extract_request_id_safely(request)
    logger.exception("SERVER_ERROR [%s]: Unhandled exception: %s", request_id, exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            request_id=request_id,
            status="error",
            error=ErrorDetail(
                code=ErrorCode.SERVER_ERROR,
                message="An unexpected server error occurred. Please try again.",
            ),
        ).model_dump(),
    )


@app.get("/")
async def root():
    return {
        "service": "Privacy-Preserving Vision Browser Agent Backend",
        "version": "1.0.0",
        "status": "running",
    }


# Mount router (exposes POST /api/v1/analyze)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("server.api:app", host="0.0.0.0", port=8000, reload=True)
