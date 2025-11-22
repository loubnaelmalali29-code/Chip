"""Main FastAPI application following OpenPoke patterns."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .logging_config import configure_logging, logger
from .routes import api_router


# Register global exception handlers for consistent error responses across the API
def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers for 422, HTTP, and 500 errors."""

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.debug("validation error", extra={"errors": exc.errors(), "path": str(request.url)})
        return JSONResponse(
            {"ok": False, "error": "Invalid request", "detail": exc.errors()},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException):
        logger.debug(
            "http error",
            extra={"detail": exc.detail, "status": exc.status_code, "path": str(request.url)},
        )
        detail = exc.detail
        if not isinstance(detail, str):
            detail = json.dumps(detail)
        return JSONResponse({"ok": False, "error": detail}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error", extra={"path": str(request.url)})
        return JSONResponse(
            {"ok": False, "error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Configure logging early
configure_logging()
_settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=_settings.app_name,
    version=_settings.app_version,
    docs_url=_settings.resolved_docs_url,
    redoc_url=None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Include aggregated router
app.include_router(api_router)


@app.on_event("startup")
async def _startup() -> None:
    """Initialize services when the app starts."""
    logger.info("Starting Chip server", extra={"version": _settings.app_version})
    
    # Connect Temporal client
    try:
        from app.services.temporal_client import get_temporal_service
        from app.temporal.schedules import ensure_schedules
        from app.temporal.worker import start_worker_background
        
        temporal_service = get_temporal_service()
        await temporal_service.connect()
        
        if temporal_service.is_available():
            # Ensure schedules are active
            client = temporal_service.get_client()
            if client:
                await ensure_schedules(client)
            
            # Start worker in background
            start_worker_background()
            logger.info("Temporal client connected and worker started")
        else:
            logger.warning("Temporal not available (server may not be running)")
    except Exception as e:
        logger.warning(f"Failed to initialize Temporal: {e}")
        logger.info("Chip will run without Temporal (no automation)")
    
    logger.info("Chip server started successfully")


@app.on_event("shutdown")
async def _shutdown() -> None:
    """Gracefully shutdown services when the app stops."""
    logger.info("Shutting down Chip server")
    
    # Gracefully close Temporal client
    try:
        from app.services.temporal_client import get_temporal_service
        temporal_service = get_temporal_service()
        if temporal_service.is_available():
            await temporal_service.close()
            logger.info("Temporal client closed")
    except Exception as e:
        logger.warning(f"Error closing Temporal client: {e}")
    
    logger.info("Chip server shutdown complete")


__all__ = ["app"]








