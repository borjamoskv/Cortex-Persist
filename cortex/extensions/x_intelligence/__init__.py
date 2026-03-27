"""CORTEX X-Intelligence Extension — Package init.

Sovereign forensic extraction from X (Twitter) via GraphQL.
Provides: XIntelligenceClient, XIntelligenceEngine, XIntelligenceDaemon.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.x_intelligence.client import XIntelligenceClient
    from cortex.extensions.x_intelligence.daemon import XIntelligenceDaemon
    from cortex.extensions.x_intelligence.engine import XIntelligenceEngine
    from cortex.extensions.x_intelligence.models import XSearchResponse, XTweet, XUser

__all__ = [
    "XIntelligenceClient",
    "XIntelligenceDaemon",
    "XIntelligenceEngine",
    "XSearchResponse",
    "XTweet",
    "XUser",
]


def __getattr__(name: str) -> object:
    """Lazy-load x_intelligence symbols (PEP 562)."""
    import importlib

    _LAZY = {
        "XIntelligenceClient": ("cortex.extensions.x_intelligence.client", "XIntelligenceClient"),
        "XIntelligenceDaemon": ("cortex.extensions.x_intelligence.daemon", "XIntelligenceDaemon"),
        "XIntelligenceEngine": ("cortex.extensions.x_intelligence.engine", "XIntelligenceEngine"),
        "XSearchResponse": ("cortex.extensions.x_intelligence.models", "XSearchResponse"),
        "XTweet": ("cortex.extensions.x_intelligence.models", "XTweet"),
        "XUser": ("cortex.extensions.x_intelligence.models", "XUser"),
    }
    if name in _LAZY:
        mod_path, attr = _LAZY[name]
        module = importlib.import_module(mod_path)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.extensions.x_intelligence' has no attribute {name!r}")
