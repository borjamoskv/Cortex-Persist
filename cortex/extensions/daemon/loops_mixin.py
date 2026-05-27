"""Background loop methods for MoskvDaemon (Seal 8 LOC extraction)."""

import logging

logger = logging.getLogger("moskv-daemon")


class LoopsMixin:
    """Mixin providing daemon background thread loop methods."""
