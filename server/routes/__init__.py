"""Router aggregation following OpenPoke patterns."""

from __future__ import annotations

from fastapi import APIRouter

# Import routers from app.routers (existing structure)
from app.routers import health as health_router_module
from app.routers import messaging as messaging_router_module

# Create aggregated router
api_router = APIRouter(prefix="/api/v1")

# Include routers
api_router.include_router(health_router_module.router)
api_router.include_router(messaging_router_module.router)

# Include agent_test router if needed (for development/testing)
try:
    from app.routers import agent_test as agent_test_router_module

    api_router.include_router(agent_test_router_module.router)
except ImportError:
    pass

__all__ = ["api_router"]






