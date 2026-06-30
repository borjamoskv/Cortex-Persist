# [C5-REAL] Exergy-Maximized
"""
Shim for backwards compatibility.
Resolves: ModuleNotFoundError: No module named 'cortex.config'
after config.py was moved to core/config.py.
"""

import sys

import babylon60.core.config as _config
from babylon60.core.config import *  # noqa: F403

# Replace this module with core.config to handle dynamic getattr if any
sys.modules[__name__] = _config
