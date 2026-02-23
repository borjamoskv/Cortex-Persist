"""CORTEX Gateway — Adapters package."""

from cortex.gateway.adapters.rest import router as rest_router
from cortex.gateway.adapters.telegram import router as telegram_router

__all__ = ["rest_router", "telegram_router"]
