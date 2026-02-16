"""
CORTEX v4.0 — API State.
Global instances and shared state for the API layer.
"""

from typing import Optional

from cortex.auth import AuthManager
from cortex.engine import CortexEngine
from cortex.timing import TimingTracker

# Globals initialized at startup in api.py lifespan
engine: Optional[CortexEngine] = None
auth_manager: Optional[AuthManager] = None
tracker: Optional[TimingTracker] = None
