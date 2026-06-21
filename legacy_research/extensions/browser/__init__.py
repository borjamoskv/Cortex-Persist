# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.browser.engine import BrowserEngine

__all__ = ["BrowserEngine"]


def __getattr__(name: str):
    if name == "BrowserEngine":
        module = importlib.import_module("cortex.extensions.browser.engine")
        value = module.BrowserEngine
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.extensions.browser' has no attribute {name!r}")
