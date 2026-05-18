"""MEV Telemetry Engine — K2 Liquidation Monitor.

Detects Liquidation Invariant Violations and Truncation Extraction attempts (K2-0514-01).
Implementación directa para CORTEX-Persist basada en los invariantes del ASL.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from cortex.engine import CortexEngine
from cortex.engine.models import Fact

logger = logging.getLogger("cortex.telemetry.mev")


@dataclass
class TelemetryAnomaly:
    type: str  # LIQUIDATION_INVARIANT_VIOLATION | TRUNCATION_EXTRACTION_ATTEMPT
    severity: str  # HIGH | MEDIUM | LOW
    facts_involved: list[int]
    description: str
    suggested_action: str


class MEVTelemetryEngine:
    """
    Monitoriza la telemetría del contrato K2 en búsqueda de violaciones de invariantes
    matemáticos y posibles vectores de extracción MEV.
    """

    def __init__(self, cortex_engine: Any, lookback_hours: int = 24):
        self.cortex = cortex_engine
        self.window = timedelta(hours=lookback_hours)
        self.anomalies: list[TelemetryAnomaly] = []

    async def run_full_scan(self) -> dict:
        """Escanea todos los eventos de liquidación recientes."""
        threshold = datetime.fromtimestamp(time.time(), tz=timezone.utc) - self.window
        time_filter = threshold.isoformat()

        recent_raw_facts = await self.cortex.history(project="k2-telemetry")
        recent_facts = [f for f in recent_raw_facts if (f.created_at or "") > time_filter]

        if not recent_facts:
            return self.generate_report()

        results = await asyncio.gather(
            self.detect_invariant_violations(recent_facts),
            self.detect_truncation_extraction(recent_facts),
        )

        self.anomalies = [a for batch in results for a in batch]
        await self.generate_verification_tasks()
        return self.generate_report()

    async def detect_invariant_violations(self, facts: list[Fact]) -> list[TelemetryAnomaly]:
        """
        Detecta liquidaciones donde HF < 1.0 y la deuda incobrable no fue socializada.
        Invariante: health_factor >= 1.0 OR bad_debt_socialized == true
        """
        violations = []
        for fact in facts:
            meta = fact.meta if isinstance(fact.meta, dict) else {}
            if meta.get("event_type") != "liquidation":
                continue

            hf = meta.get("health_factor_after", float("inf"))
            socialized = meta.get("bad_debt_socialized", False)

            if hf < 1.0 and not socialized:
                violations.append(
                    TelemetryAnomaly(
                        type="LIQUIDATION_INVARIANT_VIOLATION",
                        severity="HIGH",
                        facts_involved=[fact.id],  # type: ignore
                        description=(
                            f"Violación de invariante en fact #{fact.id}: HF posterior a liquidación "
                            f"es {hf} y la deuda no fue socializada."
                        ),
                        suggested_action="Auditar transacción on-chain inmediatamente y aislar collateral.",
                    )
                )
        return violations

    async def detect_truncation_extraction(self, facts: list[Fact]) -> list[TelemetryAnomaly]:
        """
        Detecta intentos de saltarse el parche K2-0514-01 (Ceil-Division).
        Un atacante MEV podría intentar forzar la división por truncamiento.
        """
        extractions = []
        for fact in facts:
            meta = fact.meta if isinstance(fact.meta, dict) else {}
            if meta.get("event_type") != "liquidation":
                continue

            ceil_applied = meta.get("ceil_division_applied", True)

            # Si se explícitamente reporta que no se aplicó el ceil division en un swap collateral,
            # marcamos la anomalía como intento de extracción (ataque truncado MEV).
            if not ceil_applied:
                extractions.append(
                    TelemetryAnomaly(
                        type="TRUNCATION_EXTRACTION_ATTEMPT",
                        severity="HIGH",
                        facts_involved=[fact.id],  # type: ignore
                        description=(
                            f"Posible extracción MEV en fact #{fact.id}: "
                            f"Ceil-Division bypass detectado (K2-0514-01)."
                        ),
                        suggested_action="Analizar router para confirmar pérdida de fondos por redondeo a la baja.",
                    )
                )
        return extractions

    async def generate_verification_tasks(self):
        """
        Persiste tareas de verificación en CORTEX para los operadores de seguridad.
        """
        high_severity = [a for a in self.anomalies if a.severity == "HIGH"]
        for anomaly in high_severity:
            await self.cortex.store(
                type="ghost",
                project="k2-telemetry",
                source="daemon:mev-telemetry-hunter",
                confidence="C5",
                summary=f"⚠️ ALERTA MEV/INVARIANTE: {anomaly.type}",
                meta={
                    "anomaly_type": anomaly.type,
                    "facts_involved": anomaly.facts_involved,
                    "suggested_action": anomaly.suggested_action,
                    "auto_generated": True,
                },
            )

    def generate_report(self) -> dict:
        by_type = {}
        for a in self.anomalies:
            by_type[a.type] = by_type.get(a.type, 0) + 1

        return {
            "total_anomalies": len(self.anomalies),
            "by_type": by_type,
            "high_severity": sum(1 for a in self.anomalies if a.severity == "HIGH"),
            "verification_tasks_created": sum(1 for a in self.anomalies if a.severity == "HIGH"),
        }


def start_mev_daemon(db_path: str, poll_interval_sec: int = 300) -> None:
    """Inicia el daemon de telemetría MEV en un hilo de fondo (non-blocking)."""
    import threading

    def _daemon_loop():
        # Crear un nuevo event loop para este thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Inicializar el engine dentro del loop
        engine = CortexEngine(db_path, auto_embed=False)
        telemetry = MEVTelemetryEngine(
            engine, lookback_hours=1
        )  # Lookback de 1 hora para tiempo real

        async def _scan():
            logger.info("Iniciando escaneo MEV Telemetry (K2-0514-01)...")
            while True:
                try:
                    # Requiere una conexión a la BD
                    async with engine.pool.acquire() as conn:
                        engine._conn = conn
                        report = await telemetry.run_full_scan()

                        if report["total_anomalies"] > 0:
                            logger.warning(
                                "MEV Telemetry Detectó %d anomalías (Alta severidad: %d)",
                                report["total_anomalies"],
                                report["high_severity"],
                            )
                except Exception as e:
                    logger.error("Error en MEV Telemetry Daemon: %s", e)

                await asyncio.sleep(poll_interval_sec)

        # Configurar y arrancar el pool de conexiones antes de iterar
        loop.run_until_complete(engine.pool.initialize())
        loop.run_until_complete(_scan())

    # Arrancar el thread como daemon para que no bloquee la salida del programa
    t = threading.Thread(target=_daemon_loop, name="MEVTelemetryDaemon", daemon=True)
    t.start()
    logger.info("MEV Telemetry Daemon lanzado (Polling cada %ds)", poll_interval_sec)
