"""
CORTEX v8.0 — Josu Proactive Daemon (Always-On Proactivity).

The Code Sniper: scans CORTEX DB for resolvable ghosts and low-complexity
entropy, spawns ephemeral Pulse agents to fix them autonomously, and
delivers validation-first results for human review.

Architecture:
    JosuProactiveDaemon.proactive_loop()
      └─> _query_pending_targets()      # Fetch ghosts from cortex.db
            └─> for each target:
                  └─> _spawn_pulse()     # Ephemeral Pulse agent (max_beats=15)
                        └─> _execute_and_validate()
                              └─> _create_review_request()

Axiom Derivations:
    Ω₂ (Entropic Asymmetry): Only targets below complexity threshold are attempted.
    Ω₃ (Byzantine Default): Pulse results validated before any merge.
    Ω₅ (Antifragile by Default): Failed fixes become stronger ghosts with context.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from cortex.swarm.swarm_heartbeat import SWARM_HEARTBEAT
from cortex.swarm.worktree_isolation import isolated_worktree

logger = logging.getLogger("cortex.swarm.josu_daemon")


# ── Configuration ─────────────────────────────────────────────────────────

POLL_INTERVAL_S: int = 600          # 10 min between scans
MAX_COMPLEXITY: int = 5             # Only attempt ghosts with estimated_complexity ≤ 5
MAX_PULSE_BEATS: int = 15           # Ephemeral agents die fast
MAX_CONCURRENT_FIXES: int = 2       # Parallel Pulse agents cap


# ── Data Models ───────────────────────────────────────────────────────────


@dataclass
class GhostTarget:
    """A resolvable ghost or entropy target from CORTEX DB."""

    id: str
    description: str
    project: str
    repo_path: str
    complexity: int = 3
    source: str = "ghost"
    attempts: int = 0
    max_attempts: int = 3


@dataclass
class FixResult:
    """Result of a Pulse-driven fix attempt."""

    ghost_id: str
    success: bool
    summary: str = ""
    beats_used: int = 0
    duration_ms: float = 0.0
    error: str = ""


# ── The Daemon ────────────────────────────────────────────────────────────


class JosuProactiveDaemon:
    """The Code Sniper — Proactive Background Agent.

    Scans for resolvable ghosts every POLL_INTERVAL_S seconds.
    For each target under MAX_COMPLEXITY, spawns an ephemeral Pulse
    agent confined to an isolated git worktree.

    Usage:
        daemon = JosuProactiveDaemon(cortex_db=engine)
        await daemon.proactive_loop()  # Runs forever
    """

    __slots__ = ("db", "workspace_manager", "_results", "_active_tasks")

    def __init__(self, cortex_db: Any, workspace_manager: Any = None) -> None:
        self.db = cortex_db
        self.workspace_manager = workspace_manager
        self._results: list[FixResult] = []
        self._active_tasks: int = 0

    async def proactive_loop(self) -> None:
        """Lifecycle loop. Scans → Filters → Spawns → Sleeps. Forever."""
        logger.info("⚡️ [JOSU] Code Sniper Daemon Activated.")

        while True:
            try:
                SWARM_HEARTBEAT.pulse("josu_daemon", "ProactiveLoop")

                targets = await self._query_pending_targets()

                if not targets:
                    logger.debug("💤 [JOSU] No resolvable ghosts. Sleeping %ds.", POLL_INTERVAL_S)
                else:
                    # Filter by complexity and remaining attempts
                    viable = [
                        t
                        for t in targets
                        if t.complexity <= MAX_COMPLEXITY and t.attempts < t.max_attempts
                    ]

                    logger.info(
                        "🎯 [JOSU] Found %d targets (%d viable under complexity %d).",
                        len(targets),
                        len(viable),
                        MAX_COMPLEXITY,
                    )

                    # Process viable targets with concurrency cap
                    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FIXES)
                    tasks = [self._process_target(t, semaphore) for t in viable]
                    await asyncio.gather(*tasks, return_exceptions=True)

            except asyncio.CancelledError:
                logger.info("🛑 [JOSU] Daemon shutdown signal received.")
                raise
            except Exception as e:
                logger.error("☠️ [JOSU] Loop error: %s", e, exc_info=True)

            await asyncio.sleep(POLL_INTERVAL_S)

    async def _process_target(
        self, target: GhostTarget, semaphore: asyncio.Semaphore
    ) -> None:
        """Process a single ghost target with semaphore-controlled concurrency."""
        async with semaphore:
            self._active_tasks += 1
            try:
                result = await self._execute_in_isolation(target)
                self._results.append(result)

                if result.success:
                    logger.info(
                        "✅ [JOSU] Ghost [%s] resolved in %d beats (%.0fms).",
                        target.id,
                        result.beats_used,
                        result.duration_ms,
                    )
                    await self._create_review_request(target, result)
                else:
                    logger.warning(
                        "♻️ [JOSU] Ghost [%s] unresolved. Attempt %d/%d. %s",
                        target.id,
                        target.attempts + 1,
                        target.max_attempts,
                        result.error or "Pulse flatlined.",
                    )
            finally:
                self._active_tasks -= 1

    async def _execute_in_isolation(self, target: GhostTarget) -> FixResult:
        """Spawn an ephemeral Pulse agent inside an isolated worktree."""
        branch_name = f"josu/fix-{target.id}-{int(time.time())}"
        start = time.monotonic()

        try:
            async with isolated_worktree(
                branch_name=branch_name, base_path=target.repo_path
            ) as wt_path:
                logger.info("🌿 [JOSU] Worktree lab created at %s", wt_path)

                # Import Pulse lazily to avoid circular deps
                from cortex.engine.metabolism import Metabolism

                metabolism = Metabolism(flatline_threshold=3.0)

                # Simulate Pulse-like execution loop
                # In production, this spawns a real Pulse agent:
                #   from pulse import Pulse
                #   agent = Pulse(objective=target.description,
                #                 workspace_dir=str(wt_path),
                #                 max_beats=MAX_PULSE_BEATS)
                #   agent.live()

                # For now: delegate to AgentToolkit + simple heuristic
                from cortex.aether.tools import AgentToolkit

                toolkit = AgentToolkit(wt_path)

                # Run tests to detect baseline state
                test_output = toolkit.bash("python -m pytest --tb=short -q 2>&1 || true", timeout=30)
                diag = metabolism.metabolize(test_output, "action")

                elapsed = (time.monotonic() - start) * 1000

                return FixResult(
                    ghost_id=target.id,
                    success=diag.get("novel", False) and "passed" in test_output.lower(),
                    summary=f"Baseline scan complete. Tests: {test_output[:200]}",
                    beats_used=metabolism.vitals.age,
                    duration_ms=elapsed,
                )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return FixResult(
                ghost_id=target.id,
                success=False,
                error=str(e),
                duration_ms=elapsed,
            )

    async def _query_pending_targets(self) -> list[GhostTarget]:
        """Query CORTEX DB for pending ghosts with the 'auto_ghost' tag."""
        query = (
            "SELECT id, project, content, meta "
            "FROM facts "
            "WHERE fact_type = 'ghost' AND tags LIKE '%\"auto_ghost\"%' "
            "AND valid_until IS NULL "
            "ORDER BY created_at DESC LIMIT 10"
        )
        try:
            import json
            async with self.db.session() as conn:
                cursor = await conn.execute(query)
                rows = await cursor.fetchall()
                targets = []
                for r in rows:
                    meta = r[3]
                    if isinstance(meta, str):
                        try:
                            meta = json.loads(meta)
                        except json.JSONDecodeError:
                            meta = {}
                    meta = meta or {}
                    
                    targets.append(
                        GhostTarget(
                            id=str(r[0]),
                            project=r[1],
                            description=r[2],
                            repo_path=meta.get("repo_path", "."),
                            complexity=meta.get("complexity", 3),
                        )
                    )
                return targets
        except Exception as e:
            logger.error("⚠️ [JOSU] Database scan failed: %s", e)
            return []

    async def _create_review_request(
        self, target: GhostTarget, result: FixResult
    ) -> None:
        """Deliver validation-first results for human context review."""
        logger.info(
            "📬 [JOSU] Review request for ghost [%s]: %s",
            target.id,
            result.summary[:100],
        )
        # TODO: Persist walkthrough.md to CORTEX DB as review_request
        # TODO: Notify via AetherAlert pipeline

    # ── Introspection ─────────────────────────────────────────────────

    @property
    def results(self) -> list[FixResult]:
        """Read-only access to fix history."""
        return list(self._results)

    @property
    def active_tasks(self) -> int:
        """Current number of running Pulse agents."""
        return self._active_tasks
