"""ForgettingOracle — Metacognitive forgetting: EVICTION → LEDGER → POST-HOC → POLICY."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from typing import TYPE_CHECKING, Any

from cortex.engine.forgetting_models import (
    EvictionVerdict,
    OracleReport,
    PolicyRecommendation,
)
from cortex.engine.oracle.analyzer_mixin import AnalyzerMixin
from cortex.engine.oracle.evidence_mixin import EvidenceMixin
from cortex.engine.oracle.policy_mixin import PolicyMixin
from cortex.services.notebooklm import NotebookLMService
from cortex.services.trust import TrustService

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine
    from cortex.memory.working import WorkingMemoryL1

__all__ = ["ForgettingOracle"]

logger = logging.getLogger("cortex.oracle.forgetting")


# ─── The Oracle ───────────────────────────────────────────────────────────────


class ForgettingOracle(AnalyzerMixin, PolicyMixin, EvidenceMixin):
    """Metacognitive forgetting engine (Ω₅).

    Evaluates eviction decisions and auto-adjusts cache policy.
    Uses mixins for Analyzer (eviction metrics), Policy (cache adjustments),
    and Evidence (cryptographic verification of audit trails).
    """

    # Umbrales soberanos
    REGRET_THRESHOLD = 0.20  # >20% de errores de olvido → acción
    HIGH_CAUSAL_WEIGHT_TYPES = frozenset({"axiom", "decision", "bridge", "rule"})
    CAUSAL_WEIGHT_MAP = {
        "axiom": 1.0,
        "decision": 0.9,
        "bridge": 0.8,
        "rule": 0.7,
        "knowledge": 0.5,
        "ghost": 0.4,
        "error": 0.3,
    }
    DEFAULT_WEIGHT = 0.2

    def __init__(
        self,
        engine: AsyncCortexEngine,
        cache_ref: Any = None,
        l1_ref: WorkingMemoryL1 | None = None,
    ) -> None:
        self._engine = engine
        self._cache = cache_ref
        # Direct reference to L1 Working Memory — enables real access_frequency_score
        # instead of the transactional approximation ghost (Derivation: Ω₁ + Ω₂).
        self._l1 = l1_ref
        self._last_report: OracleReport | None = None
        self._audit_count = 0

        # Ω₃/Ω₂: Integrated Services
        db_path = str(getattr(engine, "_db_path", ""))
        self._trust = TrustService(db_path) if db_path else None
        self._notebooklm = NotebookLMService(db_path) if db_path else None

    async def evaluate(self, window: int = 100) -> OracleReport:
        """Run a full forgetting audit over the last *window* evictions."""
        self._audit_count += 1
        if not self._engine:
            logger.error("🔮 [ORACLE] Oracle not initialized with an engine.")
            return self._empty_report()

        logger.info(
            "🔮 [ORACLE] Cycle #%d — Evaluating last %d evictions.",
            self._audit_count,
            window,
        )

        eviction_records = await self._fetch_eviction_records(window)

        if not eviction_records:
            return self._empty_report()

        # 1. Análisis paralelo de cada evicción
        verdict_tasks = [self._analyze_eviction(record) for record in eviction_records]
        verdicts: list[EvictionVerdict] = await asyncio.gather(*verdict_tasks)

        # 2. Métricas agregadas
        regret_rate = self._calc_regret_rate(verdicts)
        avg_value = sum(v.eviction_value for v in verdicts) / len(verdicts)

        # 3. Recomendación de política
        recommendation = self._derive_recommendation(verdicts, regret_rate)
        ttl_delta, capacity_delta = self._calc_policy_deltas(regret_rate, verdicts)

        # 4. Verificar integridad de la cadena de evidencia
        chain_valid, tip = self._verify_evidence_chain(eviction_records)

        report = OracleReport(
            audited_at=time.time(),
            window_size=len(verdicts),
            verdicts=verdicts,
            regret_rate=regret_rate,
            avg_eviction_value=avg_value,
            recommendation=recommendation,
            suggested_ttl_delta=ttl_delta,
            suggested_capacity_delta=capacity_delta,
            evidence_chain_valid=chain_valid,
            evidence_tip=tip,
        )

        self._last_report = report
        await self._persist_report(report)

        # 5. Emit signal for downstream consumers (immune, daemon)
        self._emit_audit_signal(report)

        # 6. Auto-ajuste si el umbral de arrepentimiento es crítico
        if regret_rate > self.REGRET_THRESHOLD and self._cache:
            self._apply_policy_adjustment(report)

        logger.info(
            "🔮 [ORACLE] Regret Rate: %.1f%% | Recommendation: %s | Chain: %s",
            regret_rate * 100,
            recommendation.value,
            "✅ VALID" if chain_valid else "❌ TAMPERED",
        )

        return report

    def _emit_audit_signal(self, report: OracleReport) -> None:
        """Emit oracle audit signal to the SignalBus (fire-and-forget)."""
        try:
            db_path = str(getattr(self._engine, "_db_path", ""))
            if not db_path:
                return
            from cortex.signals.bus import SignalBus

            conn = sqlite3.connect(db_path)
            try:
                bus = SignalBus(conn)
                report_dict = report.to_dict()
                payload = {
                    "regret_rate": report.regret_rate,
                    "recommendation": report.recommendation.value,
                    "window_size": report.window_size,
                    "causal_root_evictions": report_dict.get("causal_root_evictions", 0),
                    "evidence_chain_valid": report.evidence_chain_valid,
                }
                bus.emit("ORACLE_AUDIT", payload=payload, source="oracle:forgetting", project="SYSTEM")
                if report.recommendation == PolicyRecommendation.PROTECT_CAUSAL_ROOTS:
                    bus.emit(
                        "CAUSAL_ROOT_THREAT",
                        payload={k: payload[k] for k in ("regret_rate", "causal_root_evictions")},
                        source="oracle:forgetting",
                        project="SYSTEM",
                    )
            finally:
                conn.close()
        except (sqlite3.Error, ImportError, OSError) as e:
            logger.debug("[ORACLE] Signal emission failed: %s", e)

    # ─── Persistence & Reporting ───────────────────────────────────────────────

    async def _persist_report(self, report: OracleReport) -> None:
        """Persist audit report as an evolution fact in the ledger."""
        try:
            async with self._engine.session() as conn:
                await self._engine._log_transaction(
                    conn,
                    "SYSTEM",
                    "ORACLE_AUDIT",
                    report.to_dict(),
                )
                await conn.commit()
        except (sqlite3.Error, json.JSONDecodeError, TypeError) as e:
            logger.error("[ORACLE] Failed to persist report: %s", e)

    def _empty_report(self) -> OracleReport:
        return OracleReport(
            audited_at=time.time(),
            window_size=0,
            verdicts=[],
            regret_rate=0.0,
            avg_eviction_value=0.0,
            recommendation=PolicyRecommendation.OPTIMAL,
            suggested_ttl_delta=0.0,
            suggested_capacity_delta=0,
            evidence_chain_valid=True,
            evidence_tip="NO_EVICTIONS",
        )

    def should_protect(self, fact_id: int) -> bool:
        """Pre-eviction guard: returns True if evicting this fact would be regretted.

        Called by the cache layer BEFORE eviction. Prevents the regret cycle
        instead of just detecting it post-hoc.

        Criteria:
        1. Causal root: fact has descendants (depth > 0)
        2. High-access: fact is in L1 hot tier
        3. Critical type: decision, error, axiom
        """
        try:
            chain = self._engine.get_causal_chain_sync(
                fact_id=fact_id, direction="down", max_depth=1,
            )
            if chain and len(chain) > 0:
                return True

            if self._l1 and hasattr(self._l1, "get"):
                if self._l1.get(fact_id) is not None:
                    return True

            fact = self._engine.get_fact_sync(fact_id)
            if fact and fact.get("fact_type") in ("decision", "error", "axiom"):
                return True

        except (sqlite3.Error, AttributeError, OSError):
            pass

        return False

    @property
    def last_report(self) -> OracleReport | None:
        """Last generated audit report."""
        return self._last_report
