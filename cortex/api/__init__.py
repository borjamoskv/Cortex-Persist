# [C5-REAL] Exergy-Maximized

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

    app: FastAPI

__all__ = ["app"]


def __getattr__(name: str):
    if name == "app":
        from cortex.api.core import app

        return app
    raise AttributeError(f"module 'cortex.api' has no attribute {name!r}")
