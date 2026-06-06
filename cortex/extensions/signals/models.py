# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
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
        return len(self.consumed_by) > 0

    def was_consumed_by(self, consumer: str) -> bool:
        return consumer in self.consumed_by


@dataclass()
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
