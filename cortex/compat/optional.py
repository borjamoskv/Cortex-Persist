# [C5-REAL] Exergy-Maximized
"""
CORTEX - Optional dependency loader.

Centralizes lazy imports for dependencies that moved to extras.
Provides clear error messages when an optional dep is missing.
"""

from __future__ import annotations

import importlib
from typing import Any


class _LazyModule:
    """Proxy that defers ImportError until first attribute access."""

    __slots__ = ("_extra", "_module", "_name")

    def __init__(self, name: str, extra: str) -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_extra", extra)
        object.__setattr__(self, "_module", None)

    def _load(self) -> Any:
        mod = object.__getattribute__(self, "_module")
        if mod is not None:
            return mod
        name = object.__getattribute__(self, "_name")
        extra = object.__getattribute__(self, "_extra")
        try:
            mod = importlib.import_module(name)
        except ImportError as exc:
            raise ImportError(
                f"{name} is required for this feature. "
                f"Install it with: pip install cortex-persist[{extra}]"
            ) from exc
        object.__setattr__(self, "_module", mod)
        return mod

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._load(), attr)

    def __repr__(self) -> str:
        name = object.__getattribute__(self, "_name")
        mod = object.__getattribute__(self, "_module")
        if mod is not None:
            return repr(mod)
        return f"<LazyModule '{name}' (not yet loaded)>"


def require_numpy() -> Any:
    """Return numpy module or raise clear ImportError."""
    try:
        import numpy

        return numpy
    except ImportError as exc:
        raise ImportError(
            "numpy is required for this feature. "
            "Install it with: pip install cortex-persist[compute]"
        ) from exc


def require_keyring() -> Any:
    """Return keyring module or None if unavailable."""
    try:
        import keyring

        return keyring
    except ImportError:
        return None


# Pre-built lazy proxies for hot-path imports
np = _LazyModule("numpy", "compute")
