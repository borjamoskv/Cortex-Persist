"""
CORTEX v5.0 — API State.
Global instances and shared state for the API layer.
"""

from typing import Any, Optional

from cortex.auth import AuthManager
from cortex.engine import CortexEngine
from cortex.extensions.timing import TimingTracker

# Globals initialized at startup in api.py lifespan
engine: Optional[CortexEngine] = None
auth_manager: Optional[AuthManager] = None
tracker: Optional[TimingTracker] = None
notification_bus: Optional[Any] = None
