"""ForgettingAnalysisMixin — Core analysis logic for the ForgettingOracle."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import TYPE_CHECKING, Any

from cortex.engine.forgetting_models import EvictionVerdict

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cortex.oracle.forgetting.analysis")


class ForgettingAnalysisMixin:
    """Core analysis logic for the ForgettingOracle."""

    _engine: Any
    _l1: Any

    async def _fetch_eviction_records(self, window: int) -> list[dict[str, Any]]:
        """Fetch the last *window* eviction records from the ledger."""
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
        except sqlite3.Error as e:
            logger.error("[ORACLE] Database error fetching eviction records: %s", e)
            return []
        except (AttributeError, RuntimeError) as e:
            logger.error("[ORACLE] Unexpected error fetching eviction records: %s", e)
            return []

    async def _analyze_eviction(self, record: dict[str, Any]) -> EvictionVerdict:
        """Emit a verdict for a single eviction record."""
        detail = record.get("detail", {})
        audit = detail.get("audit_trail", {})
        target_key = detail.get("target_key", "unknown")
        eviction_id = audit.get("eviction_id", 0)
        reason = audit.get("reason", "unknown")

        # A. ¿Fue el key requerido de nuevo?
        was_regrettable = await self._detect_cache_miss_after_eviction(
            target_key,
            record["ts"],
        )

        # B. Peso causal + profundidad de cadena
        causal_weight, causal_depth = await self._estimate_causal_weight(
            target_key,
        )

        # C. Frecuencia de acceso
        frequency_score = await self._estimate_access_frequency(
            target_key,
            record["ts"],
        )

        # D. Valor compuesto
        eviction_value = self._compose_eviction_value(
            was_regrettable,
            causal_weight,
            frequency_score,
        )

        return EvictionVerdict(
            key=target_key,
            eviction_id=eviction_id,
            reason=reason,
            was_regrettable=was_regrettable,
            causal_weight=causal_weight,
            causal_depth=causal_depth,
            access_frequency_score=frequency_score,
            eviction_value=eviction_value,
            details={
                "tx_id": record.get("tx_id"),
                "ts": record.get("ts"),
            },
        )

    async def _detect_cache_miss_after_eviction(self, key: str, eviction_ts: str) -> bool:
        """Detect whether the evicted key was requested again after eviction."""
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
        except sqlite3.Error:
            logger.debug("[ORACLE] DB error detecting cache miss for %s", key)
            return False
        except (AttributeError, RuntimeError) as e:
            logger.debug("[ORACLE] Unexpected error detecting cache miss: %s", e)
            return False

    async def _estimate_causal_weight(self, key: str) -> tuple[float, int]:
        """Estimate causal weight (0.0→1.0) and descendant count for *key*."""
        project = key.replace("last_hash_", "") if key.startswith("last_hash_") else key
        base_weight = getattr(self, "DEFAULT_WEIGHT", 0.2)
        depth_bonus = 0.0
        max_children = 0

        try:
            async with self._engine.session() as conn:
                # A. Dominant fact type → base weight
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
                    cmap = getattr(self, "CAUSAL_WEIGHT_MAP", {})
                    base_weight = cmap.get(
                        dominant_type,
                        getattr(self, "DEFAULT_WEIGHT", 0.2),
                    )

                # B. Causal descendant count → depth bonus
                cursor = await conn.execute(
                    """
                    SELECT f.id, COUNT(c.id) as children
                    FROM facts f
                    LEFT JOIN facts c
                      ON c.parent_decision_id = f.id
                    WHERE f.project = ?
                    GROUP BY f.id
                    HAVING children > 0
                    ORDER BY children DESC
                    LIMIT 1
                    """,
                    (project,),
                )
                row = await cursor.fetchone()
                if row:
                    max_children = row[1]
                    depth_bonus = min(0.3, max_children * 0.03)

        except sqlite3.Error:
            logger.debug(
                "[ORACLE] DB error estimating causal weight for %s",
                key,
            )
        except (AttributeError, RuntimeError) as e:
            logger.debug("[ORACLE] Unexpected error estimating causal weight: %s", e)

        return min(1.0, base_weight + depth_bonus), max_children

    async def _estimate_access_frequency(self, key: str, eviction_ts: str) -> float:
        """Measure access frequency via L1 tracker (preferred) or transaction fallback."""
        project_id = (
            key.replace("last_hash_", "").split(":")[0] if key.startswith("last_hash_") else key
        )

        l1 = getattr(self, "_l1", None)
        # —— Path 1: Real L1 data ———————————————————————————————
        if l1 is not None:
            freq = l1.get_access_frequency(project_id)
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
        self,
        project_id: str,
        eviction_ts: str,
    ) -> float:
        """Transaction-count approximation of access frequency (fallback when L1 unavailable)."""
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
        except sqlite3.Error:
            logger.debug("[ORACLE] DB error in frequency fallback for %s", project_id)
            return 0.0
        except (AttributeError, RuntimeError) as e:
            logger.debug("[ORACLE] Unexpected error in frequency fallback: %s", e)
            return 0.0

    def _compose_eviction_value(
        self,
        was_regrettable: bool,
        causal_weight: float,
        frequency_score: float,
    ) -> float:
        """Composite score: 0.0 (correct eviction) → 1.0 (costly mistake)."""
        if not was_regrettable:
            return 0.0
        return (causal_weight * 0.65) + (frequency_score * 0.35)
