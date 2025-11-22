from __future__ import annotations

from fastapi import APIRouter, Depends

from server.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict:
    """Return service health status for monitoring and load balancers."""
    return {"ok": True, "service": "chip", "version": settings.app_version}


@router.get("/healthz")
async def healthz() -> dict:
    """Alternative health endpoint (kept for compatibility)."""
    return {"status": "ok"}
