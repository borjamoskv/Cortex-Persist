# [C5-REAL] Exergy-Maximized
"""Anomaly Hunter Engine - NightShift Memory Refiner.

Detects physical and temporal contradictions in the daily logs.
Direct implementation of Axiom Ω₂ (Entropic Asymmetry) and CORTEX-Sovereignty.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from cortex.engine.cognitive.models import Fact

logger = logging.getLogger("cortex.anomaly")


@dataclass
class Anomaly:
    type: str  # TEMPORAL_INVERSION | SPATIAL_CONTRADICTION | etc.
    severity: str  # HIGH | MEDIUM | LOW
    facts_involved: list[int]  # CORTEX fact IDs
    description: str
    suggested_action: str


class AnomalyHunterEngine:
    """
    Sleep-Time Compute mode: executes during NightShift (low system load).
    Analyzes all facts generated in the last 24h.
    """

    def __init__(self, cortex_engine: Any, lookback_hours: int = 24):
        self.cortex = cortex_engine
        self.window = timedelta(hours=lookback_hours)
        self.anomalies: list[Anomaly] = []

    async def _get_fact_timestamp(self, fact_id: int) -> datetime | None:
        """Helper to extract timestamp from the engine asynchronously."""
        fact_raw = await self.cortex.get_fact(fact_id)
        if not fact_raw or not fact_raw.get("created_at"):
            return None

        ts_str = fact_raw["created_at"]
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

    def _is_same_entity(self, fact_a: Fact, fact_b: Fact) -> bool:
        """Determines if two facts refer to the same entity (tags, title...)."""
        if not fact_a.tags or not fact_b.tags:
            return False
        return len(set(fact_a.tags) & set(fact_b.tags)) > 0

    def _are_contradictory(self, fact_a: Fact, fact_b: Fact) -> bool:
        """Basic heuristic for spatial contradictions."""
        a_content = fact_a.content.lower()
        b_content = fact_b.content.lower()

        # Highly simplified logic for the example, supporting English and Spanish
        is_a_blocked = "blocked" in a_content or "bloquead" in a_content
        is_b_passed = "passed" in b_content or "pasé" in b_content or "pase" in b_content

        is_b_blocked = "blocked" in b_content or "bloquead" in b_content
        is_a_passed = "passed" in a_content or "pasé" in a_content or "pase" in a_content

        if is_a_blocked and is_b_passed:
            return True
        if is_b_blocked and is_a_passed:
            return True
        return False

    async def _trace_causal_chain(self, fact: Fact) -> list[Fact]:
        """Extracts the causal chain using the hierarchy abstraction."""
        # We delegate to the engine method (which already returns list[Fact])
        chain = await self.cortex.get_causal_chain(fact.id)
        return chain if chain else []

    async def run_full_scan(self) -> dict:
        """NightShift entry point: full parallel scan."""
        threshold = datetime.fromtimestamp(time.time(), tz=timezone.utc) - self.window
        # Fetching facts from the last 24h
        time_filter = threshold.isoformat()

        # We limit the query for Nightshift (assuming there is a recall with as_of)
        # Here we use history to have all states and then filter

        # Recall relevant facts from history across tracked projects
        recent_raw_facts = await self.cortex.history(project="anomaly-hunter")
        # recent_raw_facts is now list[Fact] thanks to the update in CortexEngine
        recent_facts = [f for f in recent_raw_facts if (f.created_at or "") > time_filter]

        if not recent_facts:
            # Expand the search in a dummy way for the example
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
        Detects causes that occur AFTER their effects.
        Example: 'Imported module' timestamp > 'Created module' timestamp
        """
        inversions = []
        for fact in facts:
            if isinstance(fact.meta, dict) and fact.meta.get("caused_by"):
                cause_id = fact.meta["caused_by"]
                cause_ts = await self._get_fact_timestamp(cause_id)
                if not cause_ts:
                    continue

                # type: ignore
                effect_ts = datetime.fromisoformat(fact.created_at.replace("Z", "+00:00"))  # pyright: ignore[reportOptionalMemberAccess]

                if cause_ts > effect_ts:
                    inversions.append(
                        Anomaly(
                            type="TEMPORAL_INVERSION",
                            severity="HIGH",
                            facts_involved=[fact.id, cause_id],  # pyright: ignore
                            description=(
                                f"Effect (fact #{fact.id}) precedes its cause. "
                                f"Delta: {(cause_ts - effect_ts).seconds}s"
                            ),
                            suggested_action=(
                                "Verify timestamps of both facts. Possible logging error."
                            ),
                        )
                    )
        return inversions

    async def detect_spatial_contradictions(self, facts: list[Fact]) -> list[Anomaly]:
        """
        Two facts about the same entity with opposite states.
        Uses semantic similarity to detect 'Route X blocked' vs 'Passed through Route X'.
        """
        contradictions = []
        for i, fact_a in enumerate(facts):
            for fact_b in facts[i + 1 :]:
                if self._is_same_entity(fact_a, fact_b) and self._are_contradictory(fact_a, fact_b):
                    contradictions.append(
                        Anomaly(
                            type="SPATIAL_CONTRADICTION",
                            severity="HIGH",
                            facts_involved=[fact_a.id, fact_b.id],  # pyright: ignore
                            description=(
                                f"Contradiction between fact #{fact_a.id} and #{fact_b.id} "
                                "about the same entity."
                            ),
                            suggested_action=(
                                "Reconcile with primary source. One of the two facts is erroneous."
                            ),
                        )
                    )
        return contradictions

    async def detect_value_drift(self, facts: list[Fact]) -> list[Anomaly]:
        """Detects values that diverge drastically for the same entity."""
        drifts = []
        entity_map: dict[str, list[Fact]] = {}

        for f in facts:
            if f.tags:
                tag_key = ",".join(sorted(f.tags))
                if tag_key not in entity_map:
                    entity_map[tag_key] = []
                entity_map[tag_key].append(f)

        for tag_key, group in entity_map.items():
            if len(group) < 2:
                continue

            # Sort by time
            sorted_group = sorted(group, key=lambda x: x.created_at or "")

            for i in range(len(sorted_group) - 1):
                f1, f2 = sorted_group[i], sorted_group[i + 1]
                # Simple drift detection: if both have numerical values and they differ by > 50%
                v1 = f1.meta.get("value") if isinstance(f1.meta, dict) else None
                v2 = f2.meta.get("value") if isinstance(f2.meta, dict) else None

                if isinstance(v1, int | float) and isinstance(v2, int | float) and v1 != 0:
                    drift_pct = abs(v2 - v1) / abs(v1)
                    if drift_pct > 0.5:
                        drifts.append(
                            Anomaly(
                                type="VALUE_DRIFT",
                                severity="MEDIUM",
                                facts_involved=[f1.id, f2.id],  # type: ignore
                                description=(
                                    f"Drift detected in {tag_key}: {v1} -> {v2} ({drift_pct:.1%})"
                                ),
                                suggested_action=(
                                    "Review if the value change is legitimate or an error."
                                ),
                            )
                        )
        return drifts

    async def detect_ghost_resurrections(self, facts: list[Fact]) -> list[Anomaly]:
        """Detects entities that were deprecated ('ghost' markers) and are used again."""
        resurrections = []
        for f in facts:
            if "resurrected" in f.content.lower() or f.meta.get("reopened"):
                resurrections.append(
                    Anomaly(
                        type="GHOST_RESURRECTION",
                        severity="LOW",
                        facts_involved=[f.id],  # type: ignore
                        description=f"Entity in fact #{f.id} re-activated after supposed purge.",
                        suggested_action="Verify if the previous purge was incomplete.",
                    )
                )
        return resurrections

    async def detect_confidence_collapses(self, facts: list[Fact]) -> list[Anomaly]:
        """
        Inference chains where all sources are C3 (synthesis),
        without any anchor to C4/C5 (primary evidence).
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
                        facts_involved=[f.id for f in chain],  # pyright: ignore
                        description=(
                            f"Chain of {len(chain)} facts without C4/C5 anchor. "
                            "The entire chain is speculative."
                        ),
                        suggested_action="Search for primary source (C4/C5) or degrade the entire chain to C2.",
                    )
                )
        return collapses

    async def generate_verification_tasks(self):
        """
        For each HIGH anomaly, persists a verification task in CORTEX.
        The operator will see it at the start of the next workday.
        """
        high_severity = [a for a in self.anomalies if a.severity == "HIGH"]
        for anomaly in high_severity:
            await self.cortex.store(
                type="ghost",
                project="anomaly-hunter",
                source="daemon:anomaly-hunter-v2",
                confidence="C4",
                summary=f"⚠️ VERIFY: {anomaly.type} - {anomaly.description}",
                meta={
                    "anomaly_type": anomaly.type,
                    "facts_involved": anomaly.facts_involved,
                    "suggested_action": anomaly.suggested_action,
                    "auto_generated": True,
                    "nightshift_session": datetime.fromtimestamp(time.time(), tz=timezone.utc)
                    .date()
                    .isoformat(),
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
