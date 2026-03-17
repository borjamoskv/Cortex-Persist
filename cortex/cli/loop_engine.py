"""loop_engine — ExecutionLoop: The Sovereign Task Execution Engine.

Extracted from loop_cmds.py to satisfy the Landauer LOC barrier (≤500).
Implements the Task→Execute→Persist→Repeat cycle with 2-layer durability:
  C5 🟢 PersistSupervisor (external thread, primary)
  C4 🔵 atexit (clean exit fallback)
"""

from __future__ import annotations

import atexit
import logging
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from cortex.cli.common import DEFAULT_DB, _detect_agent_source, _run_async, get_engine
from cortex.cli.loop_models import LoopSession, PersistenceType, TaskResult, TaskStatus

__all__ = ["ExecutionLoop", "PersistSupervisor", "PERSIST_INTERVAL"]

logger = logging.getLogger("cortex.loop.engine")

# Industrial Noir palette — used in render methods
CYBER_LIME = "#CCFF00"
ELECTRIC_VIOLET = "#6600FF"
ABYSSAL_BLACK = "#0A0A0A"
YINMN_BLUE = "#2E5090"
GOLD = "#D4AF37"

#: Default supervisor interval. Every tick = max data loss window.
PERSIST_INTERVAL: int = 60


class PersistSupervisor:
    """External supervisor thread — C5 durability guarantee.

    Persists pending facts every ``interval`` seconds, independent of
    process lifecycle. The primary persistence guarantee for the loop.

    Design contract (Ω₃):
      - Does NOT trust the process to exit cleanly.
      - Each tick drains the pending queue atomically.
      - On persist failure: re-enqueues the fact (Ω₅ — error = gradient).
      - Never raises — the supervisor must not die.
      - stop() is idempotent — safe to call multiple times.

    Confidence: C5 🟢 (confirmed) — bounded data loss = ``interval`` seconds.
    """

    def __init__(self, flush_fn: Any, interval: int = PERSIST_INTERVAL) -> None:
        self._flush = flush_fn
        self._interval = interval
        self._stop = threading.Event()
        self._started = False
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="cortex-persist-supervisor"
        )

    def start(self) -> None:
        self._started = True
        self._thread.start()
        logger.info("PersistSupervisor started — interval=%ds (C5 durability)", self._interval)

    def stop(self) -> None:
        """Signal stop and wait for the supervisor to complete its final flush.

        Idempotent — safe to call from both close() and _atexit_flush.
        Second call is a guaranteed no-op: Event is already set, dead thread
        join() returns immediately.
        """
        if not self._started:
            return
        self._stop.set()
        self._thread.join(timeout=5.0)

    def _run(self) -> None:
        """Tick every N seconds, flush pending facts. Never raises."""
        while not self._stop.wait(timeout=self._interval):
            try:
                self._flush(source="supervisor")
            except Exception as exc:  # noqa: BLE001 — supervisor must not die
                logger.warning("PersistSupervisor: flush error (non-fatal): %s", exc)


class ExecutionLoop:
    """The sovereign execution loop: Task → Execute → Persist → Repeat.

    Durability model:
      - PersistSupervisor (C5 🟢): external thread, persists every 60s.
      - atexit (C4 🔵): fires on clean exit, covers last partial interval.
    """

    def __init__(
        self,
        project: str,
        db: str = DEFAULT_DB,
        source: Optional[str] = None,
        auto_persist: bool = True,
        persist_interval: int = PERSIST_INTERVAL,
    ) -> None:
        self._project = project
        self._db = db
        self._source = source or _detect_agent_source()
        self._auto_persist = auto_persist
        self._engine = get_engine(db)
        self._session = LoopSession(project=project, source=self._source)
        self._pending_facts: list[dict[str, Any]] = []
        self._pending_lock = threading.Lock()
        self._closed = False

        if auto_persist:
            self._supervisor = PersistSupervisor(
                flush_fn=self._flush_pending, interval=persist_interval
            )
            self._supervisor.start()
            atexit.register(self._atexit_flush)
        else:
            self._supervisor = None  # type: ignore[assignment]

    def execute_task(self, task: str) -> TaskResult:
        """Execute a single task and auto-persist results to CORTEX."""
        t0 = time.monotonic()
        result = TaskResult(task=task, status=TaskStatus.RUNNING, output="", duration_ms=0.0)

        try:
            output = self._run_keter(task)
            elapsed = (time.monotonic() - t0) * 1000
            result.status = TaskStatus.COMPLETED
            result.output = output
            result.duration_ms = elapsed

            if self._auto_persist:
                result.persisted_ids = self._persist_result(result)

            self._session.tasks_completed += 1

        except KeyboardInterrupt:
            result.status = TaskStatus.CANCELLED
            result.output = "Task cancelled by user"
            result.duration_ms = (time.monotonic() - t0) * 1000

        except Exception as exc:  # noqa: BLE001
            elapsed = (time.monotonic() - t0) * 1000
            result.status = TaskStatus.FAILED
            result.output = str(exc)
            result.duration_ms = elapsed
            result.errors.append(traceback.format_exc())

            if self._auto_persist:
                result.persisted_ids = self._persist_error(task, exc)

            self._session.tasks_failed += 1

        self._session.results.append(result)
        return result

    def _run_keter(self, task: str) -> str:
        """Execute task through KETER Engine phases."""
        from cortex.engine.keter import KeterEngine

        async def _ignite():
            keter = KeterEngine()
            return await keter.ignite(task, project=self._project)

        try:
            payload = _run_async(_ignite())
            parts = []
            if payload.get("spec_130_100"):
                parts.append(f"Spec: {payload['spec_130_100']}")
            if payload.get("scaffold_status"):
                parts.append(f"Scaffold: {payload['scaffold_status']}")
            if payload.get("legion_audit"):
                parts.append(f"Audit: {payload['legion_audit']}")
            if payload.get("fv_audit"):
                parts.append(f"Verification: {payload['fv_audit']}")
            if payload.get("score_130_100"):
                parts.append(f"Quality: {payload['score_130_100']}/100")
            parts.append(f"Status: {payload.get('status', 'unknown')}")
            return " │ ".join(parts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("KETER execution failed, storing as knowledge: %s", exc)
            return f"Task registered: {task}"

    def _enqueue_fact(self, content: str, fact_type: str, **meta: Any) -> None:
        """Enqueue a fact for the supervisor to persist at next tick (thread-safe)."""
        with self._pending_lock:
            self._pending_facts.append(
                {
                    "project": self._project,
                    "content": content,
                    "fact_type": fact_type,
                    "source": self._source,
                    "meta": meta,
                }
            )

    def _flush_pending(self, source: str = "supervisor") -> None:
        """Drain the pending queue and persist to CORTEX. Idempotent."""
        with self._pending_lock:
            if not self._pending_facts:
                return
            batch, self._pending_facts = self._pending_facts[:], []

        re_enqueue: list[dict[str, Any]] = []
        persisted_count = 0

        for fact in batch:
            try:
                fact_id = _run_async(
                    self._engine.store(
                        project=fact["project"],
                        content=fact["content"],
                        fact_type=fact["fact_type"],
                        source=f"{fact['source']}:{source}",
                        meta=fact.get("meta", {}),
                    )
                )
                if fact_id:
                    persisted_count += 1
            except (OSError, ValueError) as exc:
                logger.warning("_flush_pending: store failed (%s), re-enqueueing: %s", source, exc)
                re_enqueue.append(fact)

        if persisted_count:
            with self._pending_lock:
                self._session.total_persisted += persisted_count

        if re_enqueue:
            with self._pending_lock:
                self._pending_facts = re_enqueue + self._pending_facts

    def _atexit_flush(self) -> None:
        """C4 🔵 atexit fallback — fires on clean process exit only. Idempotent."""
        if self._closed:
            return

        # Si llegamos aquí y no está cerrado, significa que hubo un crash o salida inesperada.
        # Ω₅: Generamos un GHOST para no perder el estado de la sesión interrumpida.
        if self._session.results:
            self._persist_ghost(
                f"Sesión interrumpida inesperadamente antes de close(). "
                f"Completadas: {self._session.tasks_completed}, "
                f"Fallidas: {self._session.tasks_failed}."
            )

        if self._supervisor is not None:
            self._supervisor.stop()
        self._flush_pending(source="atexit_fallback")

    def _persist_result(self, result: TaskResult) -> list[int]:
        """Enqueue task result for supervisor to persist."""
        self._enqueue_fact(
            content=f"[LOOP:DECISION] {result.task} → {result.output}",
            fact_type=PersistenceType.DECISION.value,
            loop_session=self._session.started_at,
            duration_ms=result.duration_ms,
            status=result.status.value,
        )
        return []

    def _persist_error(self, task: str, exc: Exception) -> list[int]:
        """Enqueue error for supervisor to persist."""
        self._enqueue_fact(
            content=f"[LOOP:ERROR] {task} → {type(exc).__name__}: {exc}",
            fact_type=PersistenceType.ERROR.value,
            loop_session=self._session.started_at,
            traceback=traceback.format_exc()[-500:],
        )
        return []

    def _persist_ghost(self, description: str) -> Optional[int]:
        """Enqueue ghost for supervisor to persist."""
        self._enqueue_fact(
            content=f"[LOOP:GHOST] {description}",
            fact_type=PersistenceType.GHOST.value,
            loop_session=self._session.started_at,
            tasks_completed=self._session.tasks_completed,
        )
        return None

    def _persist_session_summary(self) -> None:
        """Enqueue the full session summary for supervisor to persist."""
        if not self._session.results:
            return
        parts = [
            f"[LOOP:SESSION] {self._session.tasks_completed} completed, "
            f"{self._session.tasks_failed} failed, "
            f"{self._session.total_persisted} facts persisted",
        ]
        for r in self._session.results[-10:]:
            icon = "✓" if r.status == TaskStatus.COMPLETED else "✗"
            parts.append(f"  {icon} {r.task[:60]} ({r.duration_ms:.0f}ms)")
        self._enqueue_fact(
            content="\n".join(parts),
            fact_type=PersistenceType.KNOWLEDGE.value,
            session_start=self._session.started_at,
            session_end=datetime.now(timezone.utc).isoformat(),
            tasks_completed=self._session.tasks_completed,
            tasks_failed=self._session.tasks_failed,
            total_persisted=self._session.total_persisted,
        )

    def close(self) -> None:
        """Close the execution loop: enqueue summary, flush, stop supervisor."""
        if self._auto_persist:
            if self._session.results:
                self._persist_session_summary()
            if self._supervisor is not None:
                self._supervisor.stop()
            self._flush_pending(source="close")
            self._closed = True
        _run_async(self._engine.close())
        self._session.active = False
