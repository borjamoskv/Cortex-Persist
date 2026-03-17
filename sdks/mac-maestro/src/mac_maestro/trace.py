from __future__ import annotations

from .models import RunTrace, TraceEvent


class TraceCollector:
    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def add(
        self,
        *,
        phase: str,
        action_index: int,
        action_kind: str,
        message: str,
        payload: dict | None = None,
    ) -> None:
        self._events.append(
            TraceEvent(
                phase=phase,  # type: ignore[arg-type]
                action_index=action_index,
                action_kind=action_kind,
                message=message,
                payload=payload or {},
            )
        )

    def success(self) -> RunTrace:
        return RunTrace(ok=True, events=self._events)

    def failure(self) -> RunTrace:
        return RunTrace(ok=False, events=self._events)
