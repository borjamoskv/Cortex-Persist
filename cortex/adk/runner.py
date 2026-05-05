"""Compatibility shim for the canonical ADK runner."""

import sys as _sys

from cortex.extensions.adk import runner as _canonical
from cortex.extensions.adk.runner import *  # noqa: F401,F403

_sys.modules[__name__] = _canonical
