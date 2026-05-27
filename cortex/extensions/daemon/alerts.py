"""MoskvDaemon — Alert handler mixin.

Extracted from core.py to keep file size under 300 LOC.
Each _alert_* method processes results from a specific monitor
and dispatches notifications via the Notifier subsystem.
"""

import logging
import sys
import time
from cortex.extensions.daemon.notifier import Notifier

__all__ = ["AlertHandlerMixin"]
logger = logging.getLogger("moskv-daemon")


class AlertHandlerMixin:
    """Mixin providing all alert dispatch methods for the daemon.

    Requires the host class to implement:
        - _should_alert(key: str) -> bool
        - auto_mejoralo / entropy_monitor attributes (for dispatch)
    """
