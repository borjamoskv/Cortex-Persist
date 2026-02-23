"""Perception monitor for MOSKV daemon."""

from __future__ import annotations

import logging
from typing import Any

from cortex.daemon.models import PerceptionAlert

logger = logging.getLogger("moskv-daemon")


class PerceptionMonitor:
    """Runs perception pipeline to detect workspace changes."""

    def __init__(
        self,
        workspace: str,
        interval_seconds: int = 300,
        engine: Any = None,
    ):
        self.workspace = workspace
        self.interval_seconds = interval_seconds
        self._pipeline: Any = None
        self._engine = engine

    async def _get_pipeline(self) -> Any:
        """Create pipeline lazily in async context."""
        if self._pipeline:
            return self._pipeline

        import uuid

        from cortex.engine import CortexEngine
        from cortex.perception import PerceptionPipeline

        if self._engine:
            conn = await self._engine.get_conn()
        else:
            eng = CortexEngine()
            conn = await eng.get_conn()

        session_id = "daemon-" + uuid.uuid4().hex[:8]

        self._pipeline = PerceptionPipeline(
            conn=conn,
            session_id=session_id,
            workspace=self.workspace,
        )
        self._pipeline.start()
        return self._pipeline

    async def check_async(self) -> list[PerceptionAlert]:
        """Run one check cycle. If we have a snapshot, return it as alert if confident."""
        alerts: list[PerceptionAlert] = []
        try:
            pipeline = await self._get_pipeline()
            snapshot = await pipeline.tick()
            if snapshot and snapshot.confidence and snapshot.project:
                alerts.append(
                    PerceptionAlert(
                        project=snapshot.project,
                        intent=snapshot.intent,
                        confidence=snapshot.confidence,
                        emotion=snapshot.emotion,
                        summary=snapshot.summary,
                    )
                )
        except (ValueError, OSError, RuntimeError) as e:
            logger.error("PerceptionMonitor failed: %s", e)
        return alerts

    def check(self) -> list[PerceptionAlert]:
        """Synchronous wrapper for check_async."""
        try:
            import asyncio

            return asyncio.run(self.check_async())
        except RuntimeError as e:
            if "running event loop" not in str(e):
                raise
            import asyncio

            if not hasattr(self, "_bg_tasks"):
                self._bg_tasks: set = set()

            task = asyncio.ensure_future(self.check_async())
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)
            return []
