"""MoskvDaemon — Self-healing monitor mixin.

Extracted from core.py to keep file size under 300 LOC.
Handles automatic re-instantiation of monitors that fail
more than MAX_CONSECUTIVE_FAILURES times in a row.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

__all__ = ["HealingMixin"]
logger = logging.getLogger("moskv-daemon")


class HealingMixin:
    """Mixin providing self-healing capabilities for failing monitors.

    Requires the host class to have:
        - _load_config() -> dict
        - config_dir: Path
        - _shared_engine
        - _healed_total: int
        - Individual monitor attributes (site_monitor, ghost_watcher, etc.)
    """
