"""
memento_agent.py — MementoAgent

Daemon+reactive hybrid agent that crystallizes high-value insights from
completed conversation sessions into durable cross-session memory.

Fills the gap between intra-session ops (MemoryAgent) and batch
consolidation (NightshiftAgent) by autonomously mining finished
sessions for decisions, errors, patterns, and commitments.

Pluggable extraction via the SessionExtractor protocol — callers
inject the concrete implementation (LLM-based, rule-based, etc.).

Production hardening:
    - Telemetry via MetricsRegistry (crystallization counts, latency, rejections)
    - Rate limiting per tick (max_sessions_per_tick)
    - Content hash dedup (avoids re-extracting crystallized sessions)
    - Confidence mapping to CORTEX epistemic scale (C1-C5)
    - Async-concurrent persistence within a session's insights
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any, Protocol, runtime_checkable

from cortex.agents.base import BaseAgent
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry
from cortex.memory.manager import CortexMemoryManager
from cortex.telemetry.metrics import metrics

logger = logging.getLogger(__name__)

_SUPPORTED_OPS: frozenset[str] = frozenset({"crystallize", "recall", "status"})

# ── Confidence mapping ────────────────────────────────────────────
# Maps float confidence ranges to CORTEX epistemic levels.

_CONFIDENCE_MAP: list[tuple[float, str]] = [
    (0.95, "C5"),  # Verified / execution-confirmed
    (0.85, "C4"),  # Official documentation level
    (0.70, "C3"),  # Training evaluation
    (0.50, "C2"),  # Reasonable inference
    (0.00, "C1"),  # Speculation
]

DEFAULT_MAX_SESSIONS_PER_TICK: int = 10


def _map_confidence(score: float) -> str:
    """Map a float confidence score to a CORTEX epistemic level."""
    for threshold, level in _CONFIDENCE_MAP:
        if score >= threshold:
            return level
    return "C1"


def _content_hash(content: str) -> str:
    """SHA-256 content fingerprint for deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


@runtime_checkable
class SessionExtractor(Protocol):
    """Protocol for pluggable session extraction logic."""

    async def extract(self, session_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract high-value facts from a completed session.

        Returns list of dicts with keys: content, fact_type, confidence, metadata.
        """
        ...

    async def pending_sessions(self) -> list[dict[str, Any]]:
        """Return unprocessed session payloads."""
        ...

    async def mark_processed(self, session_id: str) -> None:
        """Mark a session as crystallized."""
        ...


class MementoAgent(BaseAgent):
    """Daemon+reactive agent — crystallizes cross-conversation memory.

    On each tick, polls for unprocessed sessions via the injected
    SessionExtractor, extracts high-value facts, persists them through
    CortexMemoryManager, and emits FACT_PROPOSAL messages.

    Also responds to TASK_REQUEST messages for on-demand crystallize,
    recall, and status operations.

    Production features:
        - Prometheus-compatible metrics (crystallize counts, latency)
        - Rate-limited tick (max_sessions_per_tick)
        - Content hash deduplication
        - Confidence → C1-C5 epistemic mapping
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: SqliteMessageBus,
        tool_registry: ToolRegistry,
        manager: CortexMemoryManager,
        extractor: SessionExtractor,
        *,
        max_sessions_per_tick: int = DEFAULT_MAX_SESSIONS_PER_TICK,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._manager = manager
        self._extractor = extractor
        self._max_sessions_per_tick = max_sessions_per_tick
        self._seen_hashes: set[str] = set()

    # ------------------------------------------------------------------
    # Message handler (reactive path)
    # ------------------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind == MessageKind.SHUTDOWN:
            logger.info("MementoAgent — shutdown requested by %s", message.sender)
            self.force_stop()
            return

        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        op: str = payload.get("op", "")

        if op not in _SUPPORTED_OPS:
            await self._reply(
                message,
                {"error": f"unsupported op: {op!r}", "supported": sorted(_SUPPORTED_OPS)},
            )
            return

        try:
            result = await self._dispatch(op, payload)
            await self._reply(message, {"op": op, "result": result})
        except Exception as exc:
            logger.exception("MementoAgent op=%s failed", op)
            await self._reply(message, {"op": op, "error": str(exc)})

    # ------------------------------------------------------------------
    # Daemon tick (autonomous path)
    # ------------------------------------------------------------------

    async def tick(self) -> None:
        """Poll for unprocessed sessions and crystallize them.

        Rate-limited to max_sessions_per_tick to protect the event loop.
        """
        try:
            pending = await self._extractor.pending_sessions()
        except Exception as exc:
            logger.exception("MementoAgent — pending_sessions() failed")
            raise RuntimeError(f"SessionExtractor failure: {exc}") from exc

        if not pending:
            logger.debug("MementoAgent tick — no pending sessions")
            return

        # Rate limit: cap sessions per tick
        batch = pending[: self._max_sessions_per_tick]
        if len(pending) > self._max_sessions_per_tick:
            logger.warning(
                "MementoAgent — rate limited: %d pending, processing %d",
                len(pending),
                self._max_sessions_per_tick,
            )

        logger.info("MementoAgent — processing %d session(s)", len(batch))
        total_crystals = 0
        sessions_ok = 0

        async def _extract_only(
            session: dict[str, Any],
        ) -> tuple[dict[str, Any], list[dict[str, Any]], Exception | None]:
            try:
                # Concurrent LLM extraction and L2 fact storage
                crystals = await self._crystallize_session(session)
                return session, crystals, None
            except Exception as exc:
                return session, [], exc

        # Phase 1: Run slow LLM extractions concurrently
        results = await asyncio.gather(*[_extract_only(s) for s in batch])

        # Phase 2: Run L3 event logging sequentially to preserve cryptographic hash chain
        for session, crystals, exc in results:
            session_id = session.get("session_id", "unknown")
            if exc:
                logger.error(
                    "MementoAgent — crystallization failed for session %s: %s",
                    session_id,
                    exc,
                )
                metrics.inc(
                    "cortex_memento_errors_total",
                    {"session_id": session_id},
                )
                continue

            try:
                # Append _PROCESSED_MARKER sequentially to L3 to prevent prev_hash race conditions
                await self._extractor.mark_processed(session_id)
                sessions_ok += 1
                total_crystals += len(crystals)
            except Exception as loop_exc:
                logger.error(
                    "MementoAgent — mark_processed failed for session %s: %s",
                    session_id,
                    loop_exc,
                )
                metrics.inc(
                    "cortex_memento_errors_total",
                    {"session_id": session_id},
                )

        report = {
            "sessions_processed": sessions_ok,
            "sessions_skipped": len(pending) - len(batch),
            "crystals_emitted": total_crystals,
        }
        metrics.inc("cortex_memento_sessions_total", value=sessions_ok)
        metrics.inc("cortex_memento_crystals_total", value=total_crystals)

        await self._publish_summary(report)

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        if op == "crystallize":
            session_data = payload.get("session_data")
            if not session_data:
                raise ValueError("crystallize requires 'session_data' in payload")
            crystals = await self._crystallize_session(session_data)
            session_id = session_data.get("session_id", "unknown")
            await self._extractor.mark_processed(session_id)
            return {"session_id": session_id, "crystals": len(crystals)}

        if op == "recall":
            return await self._manager.assemble_context(
                query=payload.get("query"),
                project_id=payload.get("project_id", "default"),
                max_episodes=payload.get("max_episodes", 5),
                layer="episodic",
            )

        if op == "status":
            return {
                "agent": self.manifest.agent_id,
                "status": "ok",
                "seen_hashes": len(self._seen_hashes),
                "max_sessions_per_tick": self._max_sessions_per_tick,
            }

        raise ValueError(f"unknown op: {op!r}")

    # ------------------------------------------------------------------
    # Core crystallization
    # ------------------------------------------------------------------

    async def _crystallize_session(self, session_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract insights from a session and persist them."""
        t0 = time.perf_counter()

        insights = await self._extractor.extract(session_data)

        if not insights:
            logger.debug("MementoAgent — no insights extracted from session")
            return []

        persisted: list[dict[str, Any]] = []

        for insight in insights:
            content = insight.get("content", "")
            if not content:
                continue

            # Content hash dedup — skip already-crystallized insights
            h = _content_hash(content)
            if h in self._seen_hashes:
                logger.debug("MementoAgent — skipping duplicate content: %s", h)
                metrics.inc("cortex_memento_dedup_total")
                continue
            self._seen_hashes.add(h)

            # Map float confidence → epistemic level
            raw_confidence = insight.get("confidence", 0.7)
            epistemic_level = _map_confidence(raw_confidence)

            fact_id = await self._manager.store(
                content=content,
                project_id=session_data.get("project_id", "default"),
                fact_type=insight.get("fact_type", "memento"),
                metadata={
                    **insight.get("metadata", {}),
                    "source": "memento",
                    "session_id": session_data.get("session_id", "unknown"),
                    "confidence": raw_confidence,
                    "epistemic_level": epistemic_level,
                    "content_hash": h,
                },
                layer="episodic",
            )

            await self._emit_crystal(
                {
                    "fact_id": fact_id,
                    "content": content,
                    "fact_type": insight.get("fact_type", "memento"),
                    "epistemic_level": epistemic_level,
                }
            )
            persisted.append({"fact_id": fact_id, **insight})

        elapsed = time.perf_counter() - t0
        metrics.observe(
            "cortex_memento_crystallize_seconds",
            elapsed,
            {"session_id": session_data.get("session_id", "unknown")},
        )

        return persisted

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _emit_crystal(self, crystal: dict[str, Any]) -> None:
        msg = new_message(
            sender=self.manifest.agent_id,
            recipient="memory_agent",
            kind=MessageKind.FACT_PROPOSAL,
            payload={
                "source": "memento",
                "crystal": crystal,
            },
        )
        await self.bus.send(msg)

    async def _publish_summary(self, report: dict[str, Any]) -> None:
        targets = self.manifest.escalation_targets or []
        for target in targets:
            msg = new_message(
                sender=self.manifest.agent_id,
                recipient=target,
                kind=MessageKind.TASK_RESULT,
                payload={"memento_report": report},
            )
            await self.bus.send(msg)

    async def _reply(self, source: AgentMessage, payload: dict[str, Any]) -> None:
        reply = new_message(
            sender=self.manifest.agent_id,
            recipient=source.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=source.message_id,
        )
        await self.bus.send(reply)
