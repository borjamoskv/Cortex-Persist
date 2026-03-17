"""Anomaly Hunter Engine — NightShift Memory Refiner.

Detects physical and temporal contradictions in the daily logs.
Implementación directa del Axioma Ω₂ (Asimetría Entrópica) y CORTEX-Sovereignty.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from cortex.engine.models import Fact

logger = logging.getLogger("cortex.anomaly")


@dataclass
class Anomaly:
    type: str  # TEMPORAL_INVERSION | SPATIAL_CONTRADICTION | etc.
    severity: str  # HIGH | MEDIUM | LOW
    facts_involved: list[int]  # fact IDs de CORTEX
    description: str
    suggested_action: str


class AnomalyHunterEngine:
    """
    Modo Sleep-Time Compute: se ejecuta durante NightShift (baja carga del sistema).
    Analiza todos los facts generados en las últimas 24h.
    """

    def __init__(self, cortex_engine: Any, lookback_hours: int = 24):
        self.cortex = cortex_engine
        self.window = timedelta(hours=lookback_hours)
        self.anomalies: list[Anomaly] = []

    def _get_fact_timestamp(self, fact_id: int) -> Optional[datetime]:
        """Helper para extraer timestamp de forma síncrona si es necesario
        (En la versión final usaremos el engine async directamente).
        """
        # Para la implementación real, deberíamos hacer un fetch previo o usar async
        pass

    def _is_same_entity(self, fact_a: Fact, fact_b: Fact) -> bool:
        """Determina si dos facts hablan de la misma entidad (tags, titulo...)."""
        if not fact_a.tags or not fact_b.tags:
            return False
        return len(set(fact_a.tags) & set(fact_b.tags)) > 0

    def _are_contradictory(self, fact_a: Fact, fact_b: Fact) -> bool:
        """Heurística básica para contradicciones espaciales."""
        a_content = fact_a.content.lower()
        b_content = fact_b.content.lower()

        # Lógica muy simplificada para el ejemplo
        if "bloqueada" in a_content and "pasé" in b_content:
            return True
        if "bloqueada" in b_content and "pasé" in a_content:
            return True
        return False

    async def _trace_causal_chain(self, fact: Fact) -> list[Fact]:
        """Extrae la cadena causal usando la abstracción de hierarchy."""
        # Delegamos en el método del engine
        raw_chain = await self.cortex.get_causal_chain(fact.id)
        # Convertir diccionarios a objetos Fact para uniformidad
        # get_causal_chain devuelve dicts, simulamos tener Facts
        from cortex.engine.models import Fact

        return [Fact(**d) for d in raw_chain] if raw_chain else []

    async def run_full_scan(self) -> dict:
        """Entry point NightShift: escaneo completo en paralelo."""
        threshold = datetime.now(timezone.utc) - self.window
        # Fetching facts from the last 24h
        time_filter = threshold.isoformat()

        # Limitamos la query para Nightshift (asumiendo que hay un recall con as_of o limitamos manualmente)
        # Aquí usamos history para tener todos los estados y luego filtramos

        recent_raw_facts = await self.cortex.history(
            project="anomaly-hunter"
        )  # TODO we should scan all projects
        recent_facts = [
            Fact(**f) for f in recent_raw_facts if f.get("created_at", "") > time_filter
        ]

        if not recent_facts:
            # Amplio la busqueda de manera dummy para el ejemplo
            pass

        # Run all detectors in parallel
        results = await asyncio.gather(
            self.detect_temporal_inversions(recent_facts),
            self.detect_spatial_contradictions(recent_facts),
            self.detect_value_drift(recent_facts),
            self.detect_ghost_resurrections(recent_facts),
            self.detect_confidence_collapses(recent_facts),
        )

        self.anomalies = [a for batch in results for a in batch]
        await self.generate_verification_tasks()
        return self.generate_report()

    async def detect_temporal_inversions(self, facts: list[Fact]) -> list[Anomaly]:
        """
        Detecta causas que ocurren DESPUÉS de sus efectos.
        Ejemplo: 'Módulo importado' timestamp > 'Módulo creado' timestamp
        """
        inversions = []
        for fact in facts:
            if isinstance(fact.meta, dict) and fact.meta.get("caused_by"):
                cause_id = fact.meta["caused_by"]
                cause_raw = await self.cortex.get_fact(cause_id)
                if not cause_raw:
                    continue

                cause_time_str = cause_raw.get("created_at")
                if not cause_time_str:
                    continue

                cause_ts = datetime.fromisoformat(cause_time_str.replace("Z", "+00:00"))
                effect_ts = datetime.fromisoformat(fact.created_at.replace("Z", "+00:00"))

                if cause_ts > effect_ts:
                    inversions.append(
                        Anomaly(
                            type="TEMPORAL_INVERSION",
                            severity="HIGH",
                            facts_involved=[fact.id, cause_id],
                            description=f"Efecto (fact #{fact.id}) precede a su causa. Delta: {(cause_ts - effect_ts).seconds}s",
                            suggested_action="Verificar timestamps de ambos hechos. Posible error de registro.",
                        )
                    )
        return inversions

    async def detect_spatial_contradictions(self, facts: list[Fact]) -> list[Anomaly]:
        """
        Dos facts sobre la misma entidad con estados opuestos.
        Usa similaridad semántica para detectar 'Ruta X bloqueada' vs 'Pasé por Ruta X'.
        """
        contradictions = []
        for i, fact_a in enumerate(facts):
            for fact_b in facts[i + 1 :]:
                if self._is_same_entity(fact_a, fact_b) and self._are_contradictory(fact_a, fact_b):
                    contradictions.append(
                        Anomaly(
                            type="SPATIAL_CONTRADICTION",
                            severity="HIGH",
                            facts_involved=[fact_a.id, fact_b.id],
                            description=f"Contradicción entre fact #{fact_a.id} y #{fact_b.id} sobre la misma entidad.",
                            suggested_action="Reconciliar con fuente primaria. Uno de los dos hechos es erróneo.",
                        )
                    )
        return contradictions

    async def detect_value_drift(self, facts: list[Fact]) -> list[Anomaly]:
        """Detecta valores que divergen drásticamente en corto tiempo."""
        return []

    async def detect_ghost_resurrections(self, facts: list[Fact]) -> list[Anomaly]:
        """Detecta entidades que estaban deprecadas y vuelven a usarse."""
        return []

    async def detect_confidence_collapses(self, facts: list[Fact]) -> list[Anomaly]:
        """
        Cadenas de inferencia donde todas las fuentes son C3 (síntesis),
        sin ningún anclaje a C4/C5 (evidencia primaria).
        """
        collapses = []
        for fact in facts:
            chain = await self._trace_causal_chain(fact)
            if not chain:
                continue
            if all(f.confidence in ("C1", "C2", "C3") for f in chain) and len(chain) >= 3:
                collapses.append(
                    Anomaly(
                        type="CONFIDENCE_COLLAPSE",
                        severity="MEDIUM",
                        facts_involved=[f.id for f in chain],
                        description=f"Cadena de {len(chain)} hechos sin anclaje C4/C5. Toda la cadena es especulativa.",
                        suggested_action="Buscar fuente primaria (C4/C5) o degradar toda la cadena a C2.",
                    )
                )
        return collapses

    async def generate_verification_tasks(self):
        """
        Para cada anomalía HIGH, persiste una tarea de verificación en CORTEX.
        El operador la verá al inicio del siguiente día de trabajo.
        """
        high_severity = [a for a in self.anomalies if a.severity == "HIGH"]
        for anomaly in high_severity:
            await self.cortex.store(
                type="ghost",
                project="anomaly-hunter",
                source="daemon:anomaly-hunter-v2",
                confidence="C4",
                summary=f"⚠️ VERIFICAR: {anomaly.type} — {anomaly.description}",
                meta={
                    "anomaly_type": anomaly.type,
                    "facts_involved": anomaly.facts_involved,
                    "suggested_action": anomaly.suggested_action,
                    "auto_generated": True,
                    "nightshift_session": datetime.now(timezone.utc).date().isoformat(),
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
            "memory_health_score": max(0, 100 - len(self.anomalies) * 5),
        }
