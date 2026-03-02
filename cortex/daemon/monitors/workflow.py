"""Workflow Recommender Monitor — suggests slash commands based on system state.

Analyzes the current daemon status (ghosts, entropy, memory staleness, etc.)
and generates `WorkflowAlert`s recommending the most relevant workflow to run.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from cortex.daemon.models import AGENT_DIR, CORTEX_DB, WorkflowAlert
from cortex.daemon.monitors.base import BaseMonitor

__all__ = ["WorkflowMonitor"]

logger = logging.getLogger("moskv-daemon")

# ─── Workflow Catalog ─────────────────────────────────────────────────
# Each entry: (workflow_command, description, condition_tags)

_WORKFLOW_CATALOG: list[tuple[str, str, list[str]]] = [
    ("/josu", "Autonomous ghost resolution and code sniping", ["ghosts"]),
    ("/mejoralo", "Code quality engine — score, categorize, improve", ["entropy", "quality"]),
    ("/build", "Full quality gate — build, lint, type-check", ["quality", "build"]),
    ("/immune", "Anomaly detection, chaos gates, auto-quarantine", ["security", "anomaly"]),
    ("/nightshift", "Autonomous overnight crystal generation", ["knowledge", "stale_memory"]),
    ("/autodidact", "Semantic extraction and crystal synthesis", ["knowledge"]),
    ("/cortex-store", "Persist decisions, errors, ghosts, bridges", ["persist", "memory"]),
    ("/test", "Run test suite — full or targeted", ["quality", "tests"]),
    ("/status", "Boot protocol — load snapshot, check ghosts", ["health"]),
    ("/aether", "Autonomous agent — Executor/Planner/Critic/Tester", ["agent", "complex_task"]),
    ("/deploy", "Deploy CORTEX services — API, daemon, or MCP", ["deploy"]),
]

# Minimum seconds between re-evaluations
_EVAL_INTERVAL = 600  # 10 minutes


class WorkflowMonitor(BaseMonitor[WorkflowAlert]):
    """Monitors system conditions and recommends workflow deployments.

    Reads system signals (ghost count, memory age, engine health, etc.)
    and cross-references them against the existing workflow catalog to
    suggest the most impactful slash command to execute next.
    """

    def __init__(
        self,
        ghosts_path: Path | None = None,
        memory_path: Path | None = None,
        db_path: Path | None = None,
        *,
        ghost_stale_hours: float = 24.0,
        memory_stale_hours: float = 12.0,
        min_ghosts_for_josu: int = 2,
    ):
        self._ghosts_path = ghosts_path or (AGENT_DIR / "memory" / "ghosts.json")
        self._memory_path = memory_path or (AGENT_DIR / "memory" / "system.json")
        self._db_path = db_path or CORTEX_DB
        self._ghost_stale_hours = ghost_stale_hours
        self._memory_stale_hours = memory_stale_hours
        self._min_ghosts_for_josu = min_ghosts_for_josu
        self._last_eval: float = 0.0
        self._last_suggestions: list[WorkflowAlert] = []

    # ─── Public API ───────────────────────────────────────────────

    def check(self) -> list[WorkflowAlert]:
        """Evaluate system state and return workflow recommendations."""
        now = time.monotonic()
        if now - self._last_eval < _EVAL_INTERVAL and self._last_suggestions:
            return self._last_suggestions

        suggestions: list[WorkflowAlert] = []

        # 1. Ghost accumulation → /josu
        ghost_count = self._count_stale_ghosts()
        if ghost_count >= self._min_ghosts_for_josu:
            suggestions.append(
                WorkflowAlert(
                    workflow="/josu",
                    reason=(
                        f"{ghost_count} ghosts estancados "
                        f"(>{self._ghost_stale_hours}h). "
                        "Josu puede resolverlos."
                    ),
                    confidence="C4🔵",
                    priority=1,
                    tags=["ghosts", "autonomous"],
                )
            )

        # 2. Stale memory → /nightshift or /cortex-store
        memory_hours = self._memory_staleness_hours()
        if memory_hours is not None and memory_hours > self._memory_stale_hours:
            wf = "/nightshift" if memory_hours > 48 else "/cortex-store"
            detail = (
                "NightShift regenerará cristales."
                if wf == "/nightshift"
                else "Persiste decisiones pendientes."
            )
            suggestions.append(
                WorkflowAlert(
                    workflow=wf,
                    reason=(f"Memoria sin actualizar hace {memory_hours:.0f}h. {detail}"),
                    confidence="C4🔵",
                    priority=2 if wf == "/nightshift" else 3,
                    tags=["memory", "staleness"],
                )
            )

        # 3. DB size / health check → /build or /test
        db_size_mb = self._db_size_mb()
        if db_size_mb is not None and db_size_mb > 100:
            suggestions.append(
                WorkflowAlert(
                    workflow="/build",
                    reason=(
                        f"DB CORTEX ocupa {db_size_mb:.0f}MB. "
                        "Ejecuta build + quality gate para validar integridad."
                    ),
                    confidence="C3🟡",
                    priority=4,
                    tags=["quality", "build"],
                )
            )

        # 4. High ghost count + stale memory → /immune
        if ghost_count >= 5 and memory_hours is not None and memory_hours > 24:
            suggestions.append(
                WorkflowAlert(
                    workflow="/immune",
                    reason=(
                        f"Convergencia de {ghost_count} ghosts "
                        f"+ memoria {memory_hours:.0f}h. "
                        "Anomalía sistémica — escudos."
                    ),
                    confidence="C3🟡",
                    priority=1,
                    tags=["security", "anomaly", "convergence"],
                )
            )

        # 5. Long time since last check → /status
        if not suggestions and memory_hours is not None and memory_hours > 6:
            suggestions.append(
                WorkflowAlert(
                    workflow="/status",
                    reason=(">6h sin actividad. Reconecta con el estado del sistema."),
                    confidence="C5🟢",
                    priority=5,
                    tags=["health", "reconnect"],
                )
            )

        # Sort by priority (lower = more urgent)
        suggestions.sort(key=lambda a: a.priority)

        self._last_eval = now
        self._last_suggestions = suggestions
        return suggestions

    # ─── Private Sensors ──────────────────────────────────────────

    def _count_stale_ghosts(self) -> int:
        """Count ghosts older than threshold hours."""
        if not self._ghosts_path.exists():
            return 0
        try:
            data = json.loads(self._ghosts_path.read_text())
        except (json.JSONDecodeError, OSError):
            return 0

        now = datetime.now(timezone.utc)
        count = 0
        for _project, info in data.items():
            if not isinstance(info, dict):
                continue
            ts = info.get("timestamp", "")
            if not ts:
                continue
            if info.get("blocked_by"):
                continue
            try:
                if isinstance(ts, (int, float)):
                    last = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:
                    last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hours = (now - last).total_seconds() / 3600
                if hours > self._ghost_stale_hours:
                    count += 1
            except (ValueError, TypeError):
                continue
        return count

    def _memory_staleness_hours(self) -> float | None:
        """Return hours since system.json was last modified, or None."""
        if not self._memory_path.exists():
            return None
        try:
            mtime = self._memory_path.stat().st_mtime
            now = datetime.now(timezone.utc).timestamp()
            return (now - mtime) / 3600
        except OSError:
            return None

    def _db_size_mb(self) -> float | None:
        """Return CORTEX DB size in MB, or None."""
        db = Path(self._db_path)
        if not db.exists():
            return None
        try:
            return db.stat().st_size / (1024 * 1024)
        except OSError:
            return None
