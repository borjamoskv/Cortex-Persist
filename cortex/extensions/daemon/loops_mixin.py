"""Background loop methods for MoskvDaemon (Seal 8 LOC extraction)."""

import asyncio
import logging
import threading
import time
from cortex.extensions.daemon.models import DaemonStatus

logger = logging.getLogger("moskv-daemon")


class LoopsMixin:
    """Mixin providing daemon background thread loop methods."""
