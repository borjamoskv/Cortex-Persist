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
    "FEPMoravecGuardAdapter",
    "LedgerCheckpointHook",
    "SignalEmitHook",
    "EpistemicBreakerHook",
    "XForensicGuardAdapter",
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
    """Exergy metrics injection → ContentMutator protocol."""

    async def transform(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
    ) -> tuple[str, str, dict[str, Any]]:
        """Inject thermodynamic metrics into fact metadata (Ω₉)."""
        if project.startswith("test"):
            return content, fact_type, meta

        from cortex.engine.membrane import SovereignMembrane

        membrane = SovereignMembrane()
        result = membrane.evaluate(
            content, fact_type, counters={"source": meta.get("source") or source}
        )

        # Persist the membrane's exergy signal using the existing metadata key
        # that downstream aggregation already reads from.
        exergy_score = result.diagnostic.exergy_score
        meta["exergy_delta"] = float(exergy_score)
        meta["exergy_justification"] = "; ".join(result.diagnostic.reasons) or result.diagnostic.state.value
        if result.metadata_patch:
            meta.update(result.metadata_patch)

        return content, fact_type, meta


class XForensicGuardAdapter:
    """X-Intelligence Forensic Guard → StoreGuard protocol."""

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
        if meta.get("source") != "agent:x-intelligence":
            return

        from cortex.guards.x_guards import XForensicGuard

        guard = XForensicGuard()
        await guard.check(content, project, fact_type, meta, conn, tenant_id=tenant_id)


class FEPMoravecGuardAdapter:
    """FEP-Moravec Guard → StoreGuard protocol."""

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
        from cortex.guards.fep_moravec import FEPMoravecGuard

        guard = FEPMoravecGuard()
        await guard.check(content, project, fact_type, meta, conn, tenant_id=tenant_id)


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
        pass


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
