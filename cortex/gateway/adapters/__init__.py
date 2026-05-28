"""CORTEX Gateway — Adapters package."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.gateway.adapters.rest import router as rest_router
    from cortex.gateway.adapters.telegram import router as telegram_router

__all__ = ["rest_router", "telegram_router"]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "rest_router": ("cortex.gateway.adapters.rest", "router"),
    "telegram_router": ("cortex.gateway.adapters.telegram", "router"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.gateway.adapters' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
