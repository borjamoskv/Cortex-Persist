"""
CORTEX v5.0 — API State.
Global instances and shared state for the API layer.
"""

from __future__ import annotations

from typing import Any

from cortex.auth import AuthManager
from cortex.engine import CortexEngine
from cortex.extensions.timing import TimingTracker

# Globals initialized at startup in api.py lifespan
engine: CortexEngine | None = None
auth_manager: AuthManager | None = None
tracker: TimingTracker | None = None
notification_bus: Any | None = None
