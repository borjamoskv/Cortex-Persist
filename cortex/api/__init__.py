"""Public FastAPI entrypoints for CORTEX."""

from __future__ import annotations

__all__ = ["app"]


def __getattr__(name: str):
    if name == "app":
        from cortex.api.core import app

        return app
    raise AttributeError(f"module 'cortex.api' has no attribute {name!r}")
