"""Compatibility shim for the canonical ADK tools."""

import sys as _sys

from cortex.extensions.adk import tools as _canonical
from cortex.extensions.adk.tools import *  # noqa: F401,F403

_sys.modules[__name__] = _canonical
