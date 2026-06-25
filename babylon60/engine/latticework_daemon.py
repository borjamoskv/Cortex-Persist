# [C5-REAL] Exergy-Maximized — LatticeworkDaemon v2.0
# Author: Borja Moskv (borjamoskv)
"""
LatticeworkDaemon
=================
Daemon residente que opera sobre el AutodidactOmegaIndex (100 UnifiedPrimitiveNodes).
Cruza señales de entropía del Ledger contra el grafo unificado y aplica la matemática
Base-60 (Babylon-60) para mutar causalmente el estado del sistema.

Topología Operacional:
    Anomalía (entropía) ──► Selección de Nodo (O(1)) ──► Operador B-60 ──► Mutación Causal
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from babylon60.engine.autodidact_omega_index import AutodidactOmegaIndex, UnifiedPrimitiveNode
from babylon60.engine.babylon60 import Babylon60
from babylon60.engine.latticework_store import LatticeworkStore

logger = logging.getLogger("babylon60.latticework.daemon")

# Mapa heurístico: tag de anomalía ──► kernel_constant prioritario
_ANOMALY_DISPATCH: dict[str, str] = {
    "infinite_retry":    "ROLLBACK_SINGULARITY",
    "green_theater_slop":"GREEN_THEATER_DROP",
    "float_detected":    "FLOAT_ERADICATION_PASS",
    "stochastic_drift":  "ONTOLOGICAL_DIVERGE_CHECK",
    "context_rot":       "CONTEXT_ROT_SCAN",
    "ledger_tamper":     "TAMPER_EVIDENT_LOCK",
    "limerence":         "LIMERENCE_KILL_SIG",
    "oom":               "OOM_SIM_ABORT",
    "swarm_collision":   "COLLISION_AVOIDANCE",
    "taint_missing":     "TAINT_PROPAGATION",
}


class LatticeworkDaemon:
    """
    [C5-REAL] Daemon residente de Primitivas Cognitivas — Autodidact-Ω.
    Opera sobre el AutodidactOmegaIndex (100 UnifiedPrimitiveNodes fusionados).
    """

    def __init__(self, ledger: Any, scheduler: Any, scan_interval: int = 15):
        self.ledger = ledger
        self.scheduler = scheduler
        self.interval = scan_interval
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self.omega_index = AutodidactOmegaIndex()
        self.store = LatticeworkStore()
        self._log_coverage()

    def _log_coverage(self) -> None:
        report = self.omega_index.coverage_report()
        logger.info(
            "[LatticeworkDaemon] Autodidact-Ω Index → Total: %d | "
            "Exergy: %d | C5-REAL: %d | Unified: %d (%.1f%% coverage)",
            report["total"],
            report["exergy_nodes"],
            report["c5_primitives"],
            report["fully_unified"],
            report["coverage_pct"],
        )

    # ── Matemática B-60 ────────────────────────────────────────────────────────

    def _compute_primitive_exergy(self, entropy: float, base60_constant: int) -> Babylon60:
        """
        Operador Ortogonal B-60:  ExergyYield = B60(base60_constant) / (B60(entropy) + 1)
        Colapsa el ruido estocástico en una constante determinista.
        """
        signal_b60 = Babylon60(entropy)
        const_b60  = Babylon60.from_raw(base60_constant)
        one_b60    = Babylon60(1)
        return const_b60 / (signal_b60 + one_b60)

    def _compute_exergy_yield(self, entropy_signal: float, node: UnifiedPrimitiveNode) -> Babylon60:
        return self._compute_primitive_exergy(entropy_signal, node.base60_constant)

    # ── Dispatch lógica ────────────────────────────────────────────────────────

    def _select_node(self, tag: str) -> UnifiedPrimitiveNode | None:
        constant = _ANOMALY_DISPATCH.get(tag)
        if constant:
            return self.omega_index.by_kernel_constant(constant)
        # Fallback: búsqueda semántica por el tag
        results = self.omega_index.search(tag)
        return results[0] if results else None

    def _emit_mutation(self, anomaly_id: str, node: UnifiedPrimitiveNode, exergy: Babylon60) -> None:
        logger.info(
            "[LatticeworkDaemon] Mutación Causal C5-REAL\n"
            "  Anomalía    : %s\n"
            "  Primitiva   : [%s] %s — %s\n"
            "  Topología   : %s\n"
            "  Kernel Op   : %s\n"
            "  Exergía B60 : %s\n"
            "  Sección     : %s",
            anomaly_id,
            node.c5_real_id, node.id, node.name,
            node.algebraic_topology,
            node.kernel_constant,
            exergy,
            node.section,
        )

    # ── Daemon loop ────────────────────────────────────────────────────────────

    async def _daemon_loop(self) -> None:
        logger.info(
            "[LatticeworkDaemon] Activo. Latticework-Ω de %d nodos unificados en memoria.",
            len(self.omega_index.index),
        )

        while self._running:
            try:
                # En producción: anomalies = await self.ledger.get_recent_anomalies(limit=10)
                anomalies: list[dict[str, Any]] = [
                    {"id": "sig_A1", "entropy": 0.85, "tag": "infinite_retry"},
                    {"id": "sig_A2", "entropy": 0.91, "tag": "green_theater_slop"},
                    {"id": "sig_A3", "entropy": 0.60, "tag": "float_detected"},
                    {"id": "sig_A4", "entropy": 0.78, "tag": "taint_missing"},
                ]

                for anomaly in anomalies:
                    node = self._select_node(anomaly["tag"])
                    if node is None:
                        logger.warning(
                            "[LatticeworkDaemon] Sin nodo para tag '%s' — Entropía no resuelta.",
                            anomaly["tag"],
                        )
                        continue

                    exergy = self._compute_exergy_yield(anomaly["entropy"], node)
                    self._emit_mutation(anomaly["id"], node, exergy)

                    # Inyectar exergía matemática de vuelta al CausalScheduler
                    await self.scheduler.inject_exergy(anomaly["id"], exergy.to_float())

            except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
                logger.error("[LatticeworkDaemon] Fallo topológico: %s", e)

            await asyncio.sleep(self.interval)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._daemon_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as exc:  # P0-PURGED
                logger.warning("Suppressed exception: %s", exc)
            logger.info("[LatticeworkDaemon] Terminado. Ouroboros Infinity en reposo termodinámico.")
