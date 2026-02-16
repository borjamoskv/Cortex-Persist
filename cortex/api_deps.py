"""
CORTEX v4.0 — API Dependencies.
Shared dependencies for FastAPI routes.
"""

from __future__ import annotations
from fastapi import Request
from cortex.engine import CortexEngine
from cortex.timing import TimingTracker

def get_engine(request: Request) -> CortexEngine:
    """Inject the engine from app state."""
    return request.app.state.engine

def get_tracker(request: Request) -> TimingTracker:
    """Inject the timing tracker from app state."""
    return request.app.state.tracker
