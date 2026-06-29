# [C5-REAL] Exergy-Maximized
"""Default Guard/Hook Adapters - Wraps existing AX-II implementations behind Protocols.

Each adapter wraps a concrete module (HealthGuard, ContradictionGuard, etc.)
behind the StoreGuard / PostStoreHook protocol so they can be registered in
the GuardPipeline without store_mixin.py importing them directly.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

import aiosqlite

__all__ = [
    "ContradictionGuardAdapter",
    "EpistemicBreakerHook",
    "ExergyGuardAdapter",
    "HealthGuardAdapter",
    "LedgerCheckpointHook",
    "OmegaGuardAdapter",
    "SignalEmitHook",
    "VerifierGuardAdapter",
    "VirgoGuardAdapter",
    "ZKGuardAdapter",
    "ArchaeologyGuardAdapter",
    "OuroborosEntropyGuardAdapter",
]

logger = logging.getLogger("cortex.engine")


# ─── Pre-Store Guards ─────────────────────────────────────────────


class HealthGuardAdapter:
    """AX-II Hook 1 → StoreGuard protocol."""

    def __init__(self, engine_or_db_path: Any) -> None:
        from pathlib import Path

        if isinstance(engine_or_db_path, str) or isinstance(engine_or_db_path, Path):
            self._engine = None
            self._db_path = str(engine_or_db_path)
        else:
            self._engine = engine_or_db_path
            self._db_path = str(engine_or_db_path._db_path)

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        import time

        if self._engine is not None:
            now = time.monotonic()
            last_check = getattr(self._engine, "_last_health_check_time", 0.0)
            if now - last_check < 10.0:
                safety_ok = getattr(self._engine, "_last_health_safety_ok", True)
                if not safety_ok:
                    raise ValueError(
                        "HealthGuard blocked write operation due to degraded health (cached)"
                    )
                return

        from babylon60.guards.health_guard import HealthGuard

        guard = HealthGuard(db_path=self._db_path)
        try:
            await guard.check_write_safety()
            if self._engine is not None:
                self._engine._last_health_check_time = time.monotonic()
                self._engine._last_health_safety_ok = True
        except (ValueError, RuntimeError):
            if self._engine is not None:
                self._engine._last_health_check_time = time.monotonic()
                self._engine._last_health_safety_ok = False
            raise


class ContradictionGuardAdapter:
    """AX-II Hook 2 → StoreGuard protocol (decision/rule/error types only)."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        if fact_type not in ("decision", "rule", "error"):
            return
        from babylon60.guards.contradiction_guard import detect_contradictions

        report = await detect_contradictions(
            new_content=content, new_project=project, db_path=self._db_path
        )
        if report.has_conflicts and report.severity == "high":
            logger.warning(
                "[AX-II] Contradiction detected (severity=%s):\n%s",
                report.severity,
                report.format(),
            )


class VerifierGuardAdapter:
    """AX-II Hook 3 → StoreGuard protocol (code-type formal verification)."""

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        if fact_type != "code":
            return
        from babylon60.verification.verifier import SovereignVerifier

        result = SovereignVerifier().check(content, context={"project": project})
        if not result.is_valid:
            violation_names = [v.get("name", "unknown") for v in result.violations]
            raise ValueError(
                f"[AX-II] Formal verification failed: {violation_names}. "
                f"Counterexample: {result.counterexample}"
            )


class ExergyGuardAdapter:
    """AX-II Hook -> StoreGuard protocol (thermodynamic filter)."""

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        from babylon60.guards.exergy_guard import ExergyGuard

        guard = ExergyGuard()
        guard.check_thermodynamic_yield(content, project, fact_type, source=meta.get("source"))


class ZKGuardAdapter:
    """AX-II Hook -> StoreGuard protocol (ZK-Swarm cryptographic check)."""

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        import os

        if os.environ.get("CORTEX_TESTING") == "1":
            return
        from babylon60.guards.zk_guard import ZKSwarmGuard

        guard = ZKSwarmGuard()
        await guard.verify_integrity(content, fact_type, meta, tenant_id=tenant_id)


class VirgoGuardAdapter:
    """AX-II Hook for Logos-Critique → StoreGuard protocol."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        from babylon60.guards.virgo import VirgoContextGuard

        guard = VirgoContextGuard(engine=self._engine)
        await guard.check(content, project, fact_type, meta, conn, tenant_id=tenant_id)


class OmegaGuardAdapter:
    """AX-II Hook -> StoreGuard protocol (Omega Auditor)."""

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        import os

        # Allow bootstrap / init to skip LLM auditing for axiomatic facts.
        if os.environ.get("CORTEX_NO_OMEGA") == "1" or fact_type in (
            "mafia_node",
            "telemetry_batch",
        ):
            return

        from babylon60.guards.omega_auditor import run_omega_audit

        conflicts = await run_omega_audit(content, project)
        if conflicts:
            # Block the store
            reasons = "; ".join(
                f"[{c.severity.upper()}] {c.summary}: {c.reasoning}" for c in conflicts
            )
            raise ValueError(f"[AX-II] Omega Auditor detected contradictions: {reasons}")


class ArchaeologyGuardAdapter:
    """AX-II Hook for Archaeology First (Ley 1) → StoreGuard protocol."""

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        from babylon60.guards.archaeology_guard import ArchaeologyGuard

        guard = ArchaeologyGuard()
        result = await guard.check_history_audited(
            content, project, fact_type, meta, conn, tenant_id=tenant_id
        )
        if not result.get("allow_mutation", True):
            raise ValueError(
                f"[AX-II] Archaeology Guard blocked mutation: {result['reason']} "
                f"(trace_depth={result['trace_depth']}). Lineage/provenance gap detected."
            )


# ─── Post-Store Hooks ─────────────────────────────────────────────


class LedgerCheckpointHook:
    """AX-II Hook 4 → PostStoreHook protocol."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    async def on_stored(
        self,
        fact_id: int,
        project: str,
        fact_type: str,
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
        db_path: str | None = None,
    ) -> None:
        ledger = getattr(self._engine, "_ledger", None)
        if ledger is not None and hasattr(ledger, "record_write"):
            ledger.record_write()
            await ledger.create_checkpoint_async(conn)


class SignalEmitHook:
    """Signal emission → PostStoreHook protocol."""

    async def on_stored(
        self,
        fact_id: int,
        project: str,
        fact_type: str,
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
        db_path: str | None = None,
    ) -> None:
        from babylon60.extensions.signals.bus import AsyncSignalBus
        from babylon60.extensions.signals.fact_hook import _compact_threshold

        bus = AsyncSignalBus(conn)
        payload = {
            "fact_id": fact_id,
            "project": project,
            "fact_type": fact_type,
            "source": source or "engine:store",
            "tenant_id": tenant_id,
        }
        await bus.emit(
            "fact:stored",
            payload,
            source=source or "engine:store",
            project=project,
            tenant_id=tenant_id,
        )

        threshold = _compact_threshold()
        try:
            async with conn.execute(
                "SELECT COUNT(*) FROM signals "
                "WHERE event_type = 'fact:stored' "
                "AND project = ? "
                "AND consumed_by = '[]'",
                (project,),
            ) as cursor:
                row = await cursor.fetchone()
                unconsumed = row[0] if row else 0

            if unconsumed >= threshold:
                await bus.emit(
                    "compact:needed",
                    {
                        "project": project,
                        "unconsumed_fact_signals": unconsumed,
                        "threshold": threshold,
                        "reason": (
                            f"{unconsumed} un-consumed fact:stored signals "
                            f"exceeded threshold ({threshold})"
                        ),
                    },
                    source="fact-hook",
                    project=project,
                    tenant_id=tenant_id,
                )
                logger.info(
                    "compact:needed emitted for project=%s (unconsumed=%d)",
                    project,
                    unconsumed,
                )
        except (ValueError, RuntimeError, sqlite3.Error) as e:
            logger.debug("compact:needed check failed: %s", e)


class EpistemicBreakerHook:
    """Epistemic Circuit Breaker → PostStoreHook protocol."""

    async def on_stored(
        self,
        fact_id: int,
        project: str,
        fact_type: str,
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
        db_path: str | None = None,
    ) -> None:
        # Daemon runs asynchronously in the background.
        # Direct evaluation here is disabled until EpistemicBreakerDaemon exposes a stateless `evaluate` method.
        pass


class OuroborosEntropyGuardAdapter:
    """AX-II Hook -> StoreGuard protocol for Ouroboros entropy detection in async tasks."""

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        from babylon60.guards.ouroboros_entropy_guard import OuroborosEntropyGuard

        guard = OuroborosEntropyGuard()
        await guard.check(
            content,
            project,
            fact_type,
            meta,
            conn,
            tenant_id=tenant_id,
        )
