"""
CORTEX v6.0 — ForgettingOracle (Ω₅: Antifragile by Default).

Un sistema que solo registra lo que olvidó es contabilidad.
Un sistema que aprende de sus errores de olvido es metacognición.

El ForgettingOracle cierra el bucle:
  EVICCIÓN → LEDGER → ANÁLISIS POST-HOC → AJUSTE DE POLÍTICA → EVICCIÓN MEJORADA

Axioma: Ω₅ — el error de olvido es el gradiente más valioso del sistema.
Derivación: Ω₁ (Multi-Scale Causality) + Ω₅ (Antifragile) →
            la tasa de errores de evicción es el KPI de salud de memoria.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine
    from cortex.memory.working import WorkingMemoryL1

__all__ = ["ForgettingOracle", "EvictionVerdict", "PolicyRecommendation"]

logger = logging.getLogger("cortex.oracle.forgetting")


# ─── Domain Models ────────────────────────────────────────────────────────────


class PolicyRecommendation(Enum):
    """Ajuste de política sugerido por el Oracle."""

    OPTIMAL = "OPTIMAL"  # El sistema olvida correctamente
    INCREASE_TTL = "INCREASE_TTL"  # Olvida demasiado pronto (regret rate alto)
    REDUCE_CAPACITY = "REDUCE_CAPACITY"  # Olvida demasiado tarde (utilización OOM risk)
    PRIORITIZE_CAUSAL = "PRIORITIZE_CAUSAL"  # Olvida hechos causalmente críticos


@dataclass
class EvictionVerdict:
    """Resultado del análisis post-hoc de una evicción concreta."""

    key: str
    eviction_id: int
    reason: str
    was_regrettable: bool  # ¿Fue eviccionado algo que se necesitó después?
    causal_weight: float  # 0.0 = sin peso causal, 1.0 = axioma crítico
    access_frequency_score: float  # 0.0 = nunca accedido, 1.0 = muy frecuente
    eviction_value: float  # Score compuesto de qué tan costosa fue la decisión
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class OracleReport:
    """Informe completo de una sesión de auditoría del Oracle."""

    audited_at: float
    window_size: int
    verdicts: list[EvictionVerdict]
    regret_rate: float
    avg_eviction_value: float
    recommendation: PolicyRecommendation
    suggested_ttl_delta: float  # +N segundos o -N segundos
    suggested_capacity_delta: int  # +N items o -N items
    evidence_chain_valid: bool
    evidence_tip: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "audited_at": self.audited_at,
            "window_size": self.window_size,
            "regret_rate": self.regret_rate,
            "avg_eviction_value": self.avg_eviction_value,
            "recommendation": self.recommendation.value,
            "suggested_ttl_delta": self.suggested_ttl_delta,
            "suggested_capacity_delta": self.suggested_capacity_delta,
            "evidence_chain_valid": self.evidence_chain_valid,
            "evidence_tip": self.evidence_tip,
            "verdict_count": len(self.verdicts),
            "regrettable_evictions": sum(1 for v in self.verdicts if v.was_regrettable),
        }


# ─── The Oracle ───────────────────────────────────────────────────────────────


class ForgettingOracle:
    """
    Motor de Metacognición del Olvido (Ω₅).

    Evalúa post-hoc si las decisiones de evicción del sistema
    fueron correctas y ajusta la política de caché.

    Protocolo de análisis:
    1. Recupera las últimas N eviciones del ledger.
    2. Para cada evicción, verifica si el key fue solicitado de nuevo (cache miss).
    3. Evalúa el peso causal del dato (¿era un axiom, decision o bridge?).
    4. Calcula la tasa de arrepentimiento (regret rate).
    5. Emite una recomendación de política.
    6. Si regret_rate > REGRET_THRESHOLD, auto-ajusta los parámetros del caché.
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

    async def evaluate(self, window: int = 100) -> OracleReport:
        """
        Ejecuta una auditoría completa del olvido.

        Args:
            window: Número de eviciones a analizar.

        Returns:
            OracleReport con veredictos y recomendación de política.
        """
        self._audit_count += 1
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

        # 5. Auto-ajuste si el umbral de arrepentimiento es crítico
        if regret_rate > self.REGRET_THRESHOLD and self._cache:
            self._apply_policy_adjustment(report)

        logger.info(
            "🔮 [ORACLE] Regret Rate: %.1f%% | Recommendation: %s | Chain: %s",
            regret_rate * 100,
            recommendation.value,
            "✅ VALID" if chain_valid else "❌ TAMPERED",
        )

        return report

    # ─── Core Analysis ────────────────────────────────────────────────────────

    async def _fetch_eviction_records(self, window: int) -> list[dict[str, Any]]:
        """Recupera eviciones del ledger inmutable."""
        try:
            async with self._engine.session() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, detail, timestamp FROM transactions
                    WHERE action = 'CACHE_EVICTION'
                    ORDER BY id DESC LIMIT ?
                    """,
                    (window,),
                )
                rows = await cursor.fetchall()
                records = []
                for row in rows:
                    try:
                        detail = json.loads(row[1])
                        records.append({"tx_id": row[0], "detail": detail, "ts": row[2]})
                    except (json.JSONDecodeError, TypeError):
                        continue
                return list(reversed(records))  # Cronológico
        except (AttributeError, sqlite3.Error) as e:
            logger.error("[ORACLE] Failed to fetch eviction records: %s", e)
            return []

    async def _analyze_eviction(self, record: dict[str, Any]) -> EvictionVerdict:
        """Emite un veredicto sobre una evicción concreta."""
        detail = record.get("detail", {})
        audit = detail.get("audit_trail", {})
        target_key = detail.get("target_key", "unknown")
        eviction_id = audit.get("eviction_id", 0)
        reason = audit.get("reason", "unknown")

        # A. ¿Fue el key requerido de nuevo? (Cache Miss post-evicción)
        was_regrettable = await self._detect_cache_miss_after_eviction(target_key, record["ts"])

        # B. ¿Qué peso causal tenía el dato?
        causal_weight = await self._estimate_causal_weight(target_key)

        # C. ¿Con qué frecuencia era accedido? (aproximación)
        frequency_score = await self._estimate_access_frequency(target_key, record["ts"])

        # D. Valor compuesto de la evicción
        eviction_value = self._compose_eviction_value(
            was_regrettable, causal_weight, frequency_score
        )

        return EvictionVerdict(
            key=target_key,
            eviction_id=eviction_id,
            reason=reason,
            was_regrettable=was_regrettable,
            causal_weight=causal_weight,
            access_frequency_score=frequency_score,
            eviction_value=eviction_value,
            details={"tx_id": record.get("tx_id"), "ts": record.get("ts")},
        )

    async def _detect_cache_miss_after_eviction(self, key: str, eviction_ts: str) -> bool:
        """
        Detecta si el key eviccionado fue solicitado de nuevo después de su evicción.
        Proxy: ¿Hay transacciones 'RECALL' o 'QUERY' con este key después de la ts?
        """
        try:
            async with self._engine.session() as conn:
                # Buscamos actividad del proyecto asociado al key
                project = (
                    key.replace("last_hash_", "").split(":")[0]
                    if key.startswith("last_hash_")
                    else key
                )
                cursor = await conn.execute(
                    """
                    SELECT COUNT(*) FROM transactions
                    WHERE project = ? AND timestamp > ?
                    AND action IN ('recall', 'query', 'retrieve', 'search')
                    """,
                    (project, eviction_ts),
                )
                row = await cursor.fetchone()
                post_eviction_activity = row[0] if row else 0
                return post_eviction_activity > 0
        except (sqlite3.Error, AttributeError):
            return False

    async def _estimate_causal_weight(self, key: str) -> float:
        """
        Estima el peso causal del dato basándose en el tipo de hecho más frecuente
        del proyecto asociado.
        """
        try:
            project = key.replace("last_hash_", "") if key.startswith("last_hash_") else key
            async with self._engine.session() as conn:
                cursor = await conn.execute(
                    """
                    SELECT fact_type, COUNT(*) as cnt FROM facts
                    WHERE project = ?
                    GROUP BY fact_type ORDER BY cnt DESC LIMIT 1
                    """,
                    (project,),
                )
                row = await cursor.fetchone()
                if row:
                    dominant_type = row[0]
                    return self.CAUSAL_WEIGHT_MAP.get(dominant_type, self.DEFAULT_WEIGHT)
        except (sqlite3.Error, AttributeError):
            pass
        return self.DEFAULT_WEIGHT

    async def _estimate_access_frequency(self, key: str, eviction_ts: str) -> float:
        """Measure access frequency for a key using REAL L1 data (WorkingMemoryL1).

        Resolution order:
          1️⃣  L1 ``get_access_frequency`` — zero I/O, data from the sliding-window
             access log.  This is the canonical, non-approximated measurement.
          2️⃣  Transaction fallback — used ONLY when L1 is unavailable (testing,
             standalone Oracle, cold-start before a session has been active).

        The project_id derivation mirrors ``_detect_cache_miss_after_eviction``
        so both methods see the same namespace.
        """
        project_id = (
            key.replace("last_hash_", "").split(":")[0] if key.startswith("last_hash_") else key
        )

        # —— Path 1: Real L1 data ———————————————————————————————
        if self._l1 is not None:
            freq = self._l1.get_access_frequency(project_id)
            logger.debug(
                "[ORACLE] access_frequency_score for '%s' from L1 tracker: %.3f",
                project_id,
                freq,
            )
            return freq

        # —— Path 2: Transaction fallback (approximation) ——————————————
        logger.debug(
            "[ORACLE] L1 not available — falling back to transaction-count approximation for '%s'.",
            project_id,
        )
        return await self._estimate_access_frequency_txn_fallback(project_id, eviction_ts)

    async def _estimate_access_frequency_txn_fallback(
        self, project_id: str, eviction_ts: str
    ) -> float:
        """Transaction-count approximation of access frequency (pre-L1 integration path).

        Kept for backward-compat when the Oracle is instantiated without a live
        L1 reference (standalone testing, migrations, cold-start probes).
        """
        try:
            async with self._engine.session() as conn:
                cursor = await conn.execute(
                    """
                    SELECT COUNT(*) FROM transactions
                    WHERE project = ? AND timestamp < ?
                    """,
                    (project_id, eviction_ts),
                )
                row = await cursor.fetchone()
                count = row[0] if row else 0
                # Normalise: 100+ accesses → score 1.0
                return min(1.0, count / 100.0)
        except (sqlite3.Error, AttributeError):
            return 0.0

    def _compose_eviction_value(
        self,
        was_regrettable: bool,
        causal_weight: float,
        frequency_score: float,
    ) -> float:
        """
        Score compuesto (0.0 → evicción correcta, 1.0 → evicción muy costosa).
        Un error de olvido vale más cuando el dato era causalmente crítico Y frecuente.
        """
        if not was_regrettable:
            return 0.0
        # Ponderación: la causalidad pesa más que la frecuencia
        return (causal_weight * 0.65) + (frequency_score * 0.35)

    # ─── Policy Engine ────────────────────────────────────────────────────────

    def _calc_regret_rate(self, verdicts: list[EvictionVerdict]) -> float:
        if not verdicts:
            return 0.0
        return sum(1 for v in verdicts if v.was_regrettable) / len(verdicts)

    def _derive_recommendation(
        self,
        verdicts: list[EvictionVerdict],
        regret_rate: float,
    ) -> PolicyRecommendation:
        """Deriva la recomendación de política a partir de los veredictos."""
        if regret_rate <= 0.05:
            return PolicyRecommendation.OPTIMAL

        # ¿Qué tipo de errores predominan?
        causal_errors = [v for v in verdicts if v.was_regrettable and v.causal_weight > 0.7]
        ttl_errors = [v for v in verdicts if v.was_regrettable and v.reason == "ttl_expired"]
        lru_errors = [v for v in verdicts if v.was_regrettable and v.reason == "lru_capacity"]

        if causal_errors and len(causal_errors) > len(lru_errors):
            return PolicyRecommendation.PRIORITIZE_CAUSAL
        if len(ttl_errors) > len(lru_errors):
            return PolicyRecommendation.INCREASE_TTL
        return PolicyRecommendation.REDUCE_CAPACITY

    def _calc_policy_deltas(
        self,
        regret_rate: float,
        verdicts: list[EvictionVerdict],
    ) -> tuple[float, int]:
        """
        Calcula los deltas de TTL y capacidad a aplicar.
        La magnitud del ajuste es proporcional al error.
        """
        if regret_rate <= 0.05:
            return 0.0, 0

        # TTL: aumentar proporcionalmente al regret rate (máx +1800s)
        ttl_delta = min(1800.0, regret_rate * 3600.0)

        # Capacidad: aumentar un 15% si hay errores LRU
        lru_error_rate = sum(
            1 for v in verdicts if v.was_regrettable and v.reason == "lru_capacity"
        ) / max(len(verdicts), 1)
        capacity_delta = int(50 * lru_error_rate) if lru_error_rate > 0.1 else 0

        return ttl_delta, capacity_delta

    def _apply_policy_adjustment(self, report: OracleReport) -> None:
        """
        Auto-ajusta los parámetros del caché activo (Ω₅).
        Solo se llama cuando regret_rate > REGRET_THRESHOLD.
        """
        if not self._cache:
            return

        if report.suggested_ttl_delta > 0:
            old_ttl = self._cache.ttl
            self._cache.ttl = int(old_ttl + report.suggested_ttl_delta)
            logger.warning(
                "🔧 [ORACLE] Auto-adjusted TTL: %ds → %ds (+%.0fs)",
                old_ttl,
                self._cache.ttl,
                report.suggested_ttl_delta,
            )

        if report.suggested_capacity_delta > 0:
            old_cap = self._cache.capacity
            self._cache.capacity = old_cap + report.suggested_capacity_delta
            logger.warning(
                "🔧 [ORACLE] Auto-adjusted Capacity: %d → %d (+%d)",
                old_cap,
                self._cache.capacity,
                report.suggested_capacity_delta,
            )

    # ─── Evidence Chain Verification ──────────────────────────────────────────

    def _verify_evidence_chain(self, records: list[dict[str, Any]]) -> tuple[bool, str]:
        """Verifica que la cadena de evidencia del ledger es internamente consistente."""
        if not records:
            return True, "NO_RECORDS"

        trails = []
        for record in records:
            audit = record.get("detail", {}).get("audit_trail")
            if audit and "prev_proof" in audit and "current_proof" in audit:
                trails.append(audit)

        if not trails:
            return True, "NO_CHAIN"

        # Verificar encadenamiento
        for i in range(1, len(trails)):
            if trails[i]["prev_proof"] != trails[i - 1]["current_proof"]:
                logger.error(
                    "❌ [ORACLE] Evidence chain broken at eviction %d → %d",
                    trails[i - 1].get("eviction_id", "?"),
                    trails[i].get("eviction_id", "?"),
                )
                return False, trails[i]["prev_proof"]

        return True, trails[-1]["current_proof"]

    # ─── Persistence & Reporting ───────────────────────────────────────────────

    async def _persist_report(self, report: OracleReport) -> None:
        """Persiste el informe como 'evolution' fact en el ledger."""
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

    @property
    def last_report(self) -> OracleReport | None:
        """Último informe generado."""
        return self._last_report
