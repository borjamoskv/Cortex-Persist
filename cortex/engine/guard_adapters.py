"""Default Guard/Hook Adapters — Wraps existing AX-033 implementations behind Protocols.

Each adapter wraps a concrete module (HealthGuard, ContradictionGuard, etc.)
behind the StoreGuard / PostStoreHook protocol so they can be registered in
the GuardPipeline without store_mixin.py importing them directly.
"""

from __future__ import annotations

import logging
from typing import Any

import aiosqlite

__all__ = [
    "HealthGuardAdapter",
    "ContradictionGuardAdapter",
    "VerifierGuardAdapter",
    "ExergyGuardAdapter",
    "LedgerCheckpointHook",
    "SignalEmitHook",
    "EpistemicBreakerHook",
]

logger = logging.getLogger("cortex.engine")


# ─── Pre-Store Guards ─────────────────────────────────────────────


class HealthGuardAdapter:
    """AX-033 Hook 1 → StoreGuard protocol."""

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
        from cortex.guards.health_guard import HealthGuard

        guard = HealthGuard(db_path=self._db_path)
        await guard.check_write_safety()


class ContradictionGuardAdapter:
    """AX-033 Hook 2 → StoreGuard protocol (decision/rule/error types only)."""

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
        from cortex.guards.contradiction_guard import detect_contradictions

        report = await detect_contradictions(
            new_content=content, new_project=project, db_path=self._db_path
        )
        if report.has_conflicts and report.severity == "high":
            logger.warning(
                "[AX-033] Contradiction detected (severity=%s):\n%s",
                report.severity,
                report.format(),
            )


class VerifierGuardAdapter:
    """AX-033 Hook 3 → StoreGuard protocol (code-type formal verification)."""

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
        from cortex.verification.verifier import SovereignVerifier

        result = SovereignVerifier().check(content, context={"project": project})
        if not result.is_valid:
            violation_names = [v.get("name", "unknown") for v in result.violations]
            raise ValueError(
                f"[AX-033] Formal verification failed: {violation_names}. "
                f"Counterexample: {result.counterexample}"
            )


class ExergyGuardAdapter:
    """AX-033 Hook -> StoreGuard protocol (thermodynamic filter)."""

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
        from cortex.guards.exergy_guard import ExergyGuard

        guard = ExergyGuard()
        guard.check_thermodynamic_yield(content, project, fact_type, source=meta.get("source"))


# ─── Post-Store Hooks ─────────────────────────────────────────────


class LedgerCheckpointHook:
    """AX-033 Hook 4 → PostStoreHook protocol."""

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
            await ledger.create_checkpoint_async()


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
        from cortex.extensions.signals.fact_hook import emit_fact_stored

        if db_path:
            emit_fact_stored(
                db_path=db_path,
                fact_id=fact_id,
                project=project,
                fact_type=fact_type,
                source=source or "engine:store",
                tenant_id=tenant_id,
            )


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
        from cortex.extensions.daemon.epistemic_breaker import EpistemicBreakerDaemon

        await EpistemicBreakerDaemon.evaluate(  # type: ignore[reportAttributeAccessIssue]
            conn,
            tenant_id,
            project,
        )
