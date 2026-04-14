"""Public FastAPI entrypoints for CORTEX."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["app"]

if TYPE_CHECKING:
    from fastapi import FastAPI
    from cortex.api.core import app as app


def __getattr__(name: str) -> Any:
    if name == "app":
        from cortex.api.core import app

        return app
    raise AttributeError(f"module 'cortex.api' has no attribute {name!r}")
