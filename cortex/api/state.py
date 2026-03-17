"""
CORTEX v5.0 — API State.
Global instances and shared state for the API layer.
"""

<<<<<<< HEAD
from typing import Any
=======
from typing import Any, Optional
>>>>>>> origin/main

from cortex.auth import AuthManager
from cortex.engine import CortexEngine
from cortex.extensions.timing import TimingTracker

# Globals initialized at startup in api.py lifespan
<<<<<<< HEAD
engine: CortexEngine | None = None
auth_manager: AuthManager | None = None
tracker: TimingTracker | None = None
notification_bus: Any | None = None
=======
engine: Optional[CortexEngine] = None
auth_manager: Optional[AuthManager] = None
tracker: Optional[TimingTracker] = None
notification_bus: Optional[Any] = None
>>>>>>> origin/main
