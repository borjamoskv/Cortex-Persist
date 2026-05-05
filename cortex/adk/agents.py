"""Compatibility shim for the canonical ADK agent definitions."""

import sys as _sys

from cortex.extensions.adk import agents as _canonical
from cortex.extensions.adk.agents import *  # noqa: F401,F403

_sys.modules[__name__] = _canonical
