"""Compatibility shim for the canonical Google One ADK tools."""

import sys as _sys

from cortex.extensions.adk import goog_tools as _canonical
from cortex.extensions.adk.goog_tools import *  # noqa: F401,F403

_sys.modules[__name__] = _canonical
