"""
CORTEX v5.0 — API State.
Global instances and shared state for the API layer.
"""

from cortex.auth import AuthManager
from cortex.engine import CortexEngine
from cortex.timing import TimingTracker

# Globals initialized at startup in api.py lifespan
engine: CortexEngine | None = None
auth_manager: AuthManager | None = None
tracker: TimingTracker | None = None
