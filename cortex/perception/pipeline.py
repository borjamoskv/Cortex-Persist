"""
CORTEX v5.0 — Perception Layer 3: Recorder & Pipeline.

Auto-records behavioral snapshots to episodic memory
and orchestrates the full perception pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from cortex.episodic.main import EpisodicMemory
from cortex.perception.base import (
    INFERENCE_WINDOW_SECONDS,
    MIN_EVENTS_FOR_INFERENCE,
    RECORD_COOLDOWN_SECONDS,
    BehavioralSnapshot,
    FileEvent,
)

from .inference import infer_behavior
from .observer import FileActivityObserver

__all__ = ["PerceptionPipeline", "PerceptionRecorder"]

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.perception")


class PerceptionRecorder:
    """Auto-records behavioral snapshots to episodic memory.

    Rate-limited to avoid overwhelming the episode store.
    Only records when inference confidence >= C3.
    """

    MIN_CONFIDENCE = {"C3", "C4", "C5"}

    def __init__(
        self,
        conn: aiosqlite.Connection,
        session_id: str,
        cooldown_s: float = RECORD_COOLDOWN_SECONDS,
    ) -> None:
        self.memory = EpisodicMemory(conn)
        self.session_id = session_id
        self.cooldown_s = cooldown_s
        self._last_record: dict[str, float] = {}  # project -> timestamp

    async def maybe_record(self, snapshot: BehavioralSnapshot) -> int | None:
        """Record a snapshot if confidence is high enough and cooldown has passed.

        Returns:
            Episode ID if recorded, None if skipped.
        """
        if snapshot.confidence not in self.MIN_CONFIDENCE:
            return None

        # Rate limit per project
        project_key = snapshot.project or "__global__"
        now = time.monotonic()
        last = self._last_record.get(project_key, 0)
        if now - last < self.cooldown_s:
            return None

        self._last_record[project_key] = now

        # Map intent to episodic event type
        event_type_map = {
            "debugging": "discovery",
            "setup": "decision",
            "deep_work": "flow_state",
            "experimenting": "discovery",
            "frustrated_iteration": "blocked",
            "documenting": "milestone",
            "refactoring": "decision",
        }
        event_type = event_type_map.get(snapshot.intent, "insight")

        episode_id = await self.memory.record(
            session_id=self.session_id,
            event_type=event_type,
            content=snapshot.summary,
            project=snapshot.project,
            emotion=snapshot.emotion,
            tags=["auto-perceived", "behavioral"],
            meta=snapshot.to_dict(),
        )

        logger.info(
            "Auto-recorded episode #%d: %s (%s)",
            episode_id,
            snapshot.intent,
            snapshot.confidence,
        )
        return episode_id


class PerceptionPipeline:
    """Complete perception pipeline combining all 3 layers.

    Usage:
        pipeline = PerceptionPipeline(conn, session_id, workspace)
        pipeline.start()
        # ... runs in background, auto-records episodes
        pipeline.stop()
    """

    def __init__(
        self,
        conn: aiosqlite.Connection,
        session_id: str,
        workspace: str,
        window_s: float = INFERENCE_WINDOW_SECONDS,
        cooldown_s: float = RECORD_COOLDOWN_SECONDS,
    ) -> None:
        self.workspace = workspace
        self.window_s = window_s
        self._events: list[FileEvent] = []
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

        self.recorder = PerceptionRecorder(conn, session_id, cooldown_s)
        self.observer = FileActivityObserver(
            workspace=workspace,
            callback=self._on_event,
        )

    def _on_event(self, event: FileEvent) -> None:
        """Callback from the watchdog thread — thread-safe append."""
        self._events.append(event)

    def start(self) -> None:
        """Start the observer."""
        self.observer.start()
        logger.info("PerceptionPipeline started: %s", self.workspace)

    def stop(self) -> None:
        """Stop the observer."""
        self.observer.stop()
        logger.info("PerceptionPipeline stopped")

    @property
    def is_alive(self) -> bool:
        return self.observer.is_alive

    def get_window_events(self) -> list[FileEvent]:
        """Get events within the current inference window."""
        now = time.monotonic()
        cutoff = now - self.window_s
        # Prune old events
        self._events = [e for e in self._events if e.timestamp >= cutoff]
        return list(self._events)

    async def tick(self) -> BehavioralSnapshot | None:
        """Run one inference cycle.

        Call this periodically (e.g. every 30s) to process accumulated events.

        Returns:
            BehavioralSnapshot if inference was made, None if insufficient data.
        """
        events = self.get_window_events()
        if len(events) < MIN_EVENTS_FOR_INFERENCE:
            return None

        snapshot = infer_behavior(events)
        await self.recorder.maybe_record(snapshot)
        return snapshot

    @property
    def event_count(self) -> int:
        return len(self._events)
