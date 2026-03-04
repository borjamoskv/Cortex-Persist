# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v6.0 — Signal Bus Models.

Lightweight dataclasses for signal persistence and filtering.
Zero external dependencies beyond stdlib.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Signal:
    """An immutable signal persisted in SQLite."""

    id: int
    event_type: str
    payload: dict
    source: str
    project: str | None
    created_at: datetime
    consumed_by: list[str]

    @property
    def is_consumed(self) -> bool:
        """True if at least one consumer has processed this signal."""
        return len(self.consumed_by) > 0

    def was_consumed_by(self, consumer: str) -> bool:
        """Check if a specific consumer already processed this signal."""
        return consumer in self.consumed_by


@dataclass(slots=True)
class SignalFilter:
    """Query filter for signal retrieval."""

    event_type: str | None = None
    source: str | None = None
    project: str | None = None
    since: datetime | None = None
    consumer: str | None = None
    unconsumed_only: bool = False


def signal_from_row(row: tuple) -> Signal:
    """Convert a database row to a Signal model."""
    raw_ts = row[5]
    ts = datetime.fromisoformat(raw_ts) if isinstance(raw_ts, str) else raw_ts
    raw_consumed = row[6]
    consumed = json.loads(raw_consumed) if raw_consumed else []
    return Signal(
        id=row[0],
        event_type=row[1],
        payload=json.loads(row[2]) if isinstance(row[2], str) else row[2],
        source=row[3],
        project=row[4],
        created_at=ts,
        consumed_by=consumed,
    )
