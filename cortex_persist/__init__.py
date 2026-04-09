"""Public import alias for the ``cortex-persist`` distribution.

The package published to PyPI uses the normalized project name ``cortex-persist``.
This module provides the matching ``cortex_persist`` import surface without
forcing consumers to know the internal ``cortex`` package layout.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from cortex import __version__

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "AsyncCortexClient": ("cortex.api.async_client", "AsyncCortexClient"),
    "CortexClient": ("cortex.api.client", "CortexClient"),
    "CortexEngine": ("cortex", "CortexEngine"),
}


def __getattr__(name: str) -> Any:
    """Lazily expose the supported public API for the packaged distribution."""
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module 'cortex_persist' has no attribute {name!r}")

    module_name, attr_name = _LAZY_IMPORTS[name]
    module = import_module(module_name)
    attr = getattr(module, attr_name)
    globals()[name] = attr
    return attr


__all__ = [
    "AsyncCortexClient",
    "CortexClient",
    "CortexEngine",
    "__version__",
]
