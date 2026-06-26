# [C5-REAL] Exergy-Maximized
"""
API Dependencies.
Shared dependencies for FastAPI routes.
"""

from fastapi import Request

from cortex.engine import CortexEngine
from cortex.engine import CortexEngine as AsyncCortexEngine
from cortex_extensions.timing import TimingTracker

__all__ = ["get_async_engine", "get_engine", "get_tracker"]


def get_engine(request: Request) -> CortexEngine:
    """Inject the legacy sync-wrapped engine from app state."""
    return request.app.state.engine


def get_async_engine(request: Request) -> AsyncCortexEngine:
    """Inject the native async engine (Wave 5)."""
    return request.app.state.async_engine


def get_tracker(request: Request) -> TimingTracker:
    """Inject the timing tracker from app state."""
    return request.app.state.tracker
