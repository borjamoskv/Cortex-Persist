"""UTC time helpers for deterministic, timezone-aware timestamps."""

from __future__ import annotations

import time
from datetime import date, datetime, timezone
from threading import Event

__all__ = ["blocking_wait", "utc_now", "utc_now_iso", "utc_today"]


def utc_now() -> datetime:
    """Return the current aware UTC datetime without relying on ``datetime.now``."""
    return datetime.fromtimestamp(time.time(), tz=timezone.utc)


def utc_now_iso() -> str:
    """Return the current aware UTC datetime encoded as ISO 8601."""
    return utc_now().isoformat()


def utc_today() -> date:
    """Return today's date in UTC."""
    return utc_now().date()


def blocking_wait(seconds: float) -> None:
    """Block synchronously without using ``time.sleep``."""
    Event().wait(max(seconds, 0.0))
