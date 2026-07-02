# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Adaptive Resonance Gate (ART-inspired).

Implements Grossberg's Adaptive Resonance Theory as a pre-store filter.
Instead of blindly appending facts, the gate checks for semantic resonance
with existing engrams. If resonance is found (similarity > ρ), LTP is applied.
If not, a new engram is created.

Strategy 2: Eliminates semantic duplication at the source.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from babylon60.memory.engrams import CortexSemanticEngram
from babylon60.telemetry.metrics import metrics

if TYPE_CHECKING:
    from babylon60.extensions.sovereign.endocrine import DigitalEndocrine

logger = logging.getLogger("babylon60.memory.resonance")


def cosine_similarity(
    a: list[float] | list[int] | bytes, b: list[float] | list[int] | bytes
) -> float:
    """Compute cosine similarity between two vectors, supporting int8 bytes representations."""
    import numpy as np

    def _to_array(v: Any) -> np.ndarray:
        if isinstance(v, bytes):
            return np.frombuffer(v, dtype=np.int8).astype(np.float32)
        return np.array(v, dtype=np.float32)

    arr_a = _to_array(a)
    arr_b = _to_array(b)

    if arr_a.size != arr_b.size or arr_a.size == 0:
        return 0.0

    dot = np.dot(arr_a, arr_b)
    norm_a = np.linalg.norm(arr_a)
    norm_b = np.linalg.norm(arr_b)

    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return float(dot / (norm_a * norm_b))


def is_less_than_c5(confidence_val: Any) -> bool:
    """Return True if confidence is explicitly less than C5/1.0, or not C5/1.0."""
    if not confidence_val:
        return True
    val_str = str(confidence_val).strip().upper()
    if val_str in ("C5", "1.0", "1"):
        return False
    return True


def confidence_to_float(c_val: Any) -> float:
    """Map ordinal confidence levels or strings to float weights [0.0 - 1.0]."""
    if not c_val:
        return 0.5
    val_str = str(c_val).strip().upper()
    mapping = {
        "C5": 1.0,
        "C4": 0.8,
        "C3": 0.6,
        "C2": 0.4,
        "C1": 0.2,
        "1.0": 1.0,
        "0.8": 0.8,
        "0.6": 0.6,
        "0.4": 0.4,
        "0.2": 0.2,
    }
    try:
        return mapping.get(val_str, float(val_str))
    except ValueError:
        return 0.5


def get_confidence_val(engram: Any) -> Any:
    """Extract confidence cleanly prioritizing metadata over class attributes."""
    if hasattr(engram, "metadata") and engram.metadata and "confidence_score" in engram.metadata:
        return engram.metadata["confidence_score"]
    return getattr(engram, "confidence", None)


class AdaptiveResonanceGate:
    """ART-v2 inspired gate that controls memory write operations.

    The vigilance parameter ρ (rho) determines the threshold for
    pattern matching.

    Enhancements for v6.1:
    - Dynamic Rho: Adjusts vigilance based on context (Precision vs Recall modes).
    - Topographic Boost: Resonates with physical "ghosts" in the filesystem field.
    - Metabolic Filtering: Incorporates engram energy levels into resonance probability.
    """

    def __init__(
        self,
        vector_store: Any,
        rho: float = 0.85,
        ltp_boost: float = 0.25,
        songline_sensor: Any | None = None,
        endocrine: DigitalEndocrine | None = None,
    ):
        self._vs = vector_store
        self._rho = rho
        self._ltp_boost = ltp_boost
        self._sensor = songline_sensor
        self._endocrine = endocrine

    def _calculate_topographic_boost(self, candidate: CortexSemanticEngram) -> float:
        """Evaluate if the candidate resonates with any physical 'ghosts' in its field."""
        if not self._sensor or not hasattr(candidate, "source_file"):
            return 0.0

        # Optional: scan field around the source file
        try:
            from pathlib import Path

            field = self._sensor.scan_field(Path(candidate.source_file).parent)  # type: ignore[type-error]
            # Find ghosts matching intent or project
            for ghost in field:
                if ghost.get("project") == candidate.project:  # type: ignore[type-error]
                    # Found a physical trace of the same project context
                    return 0.05  # Static boost for topographic proximity
        except (OSError, AttributeError, TypeError) as exc:
            logger.debug(
                "Topographic boost unavailable for engram %s: %s",
                getattr(candidate, "id", "?"),
                exc,
            )

        return 0.0

    def _calculate_endocrine_shift(self) -> float:
        """Modulate vigilance based on biological system state.

        Cortisol (Stress) -> Increases rho (Stricter matching, defensive)
        Dopamine (Creativity) -> Decreases rho (Broader resonance, exploratory)
        """
        if not self._endocrine:
            return 0.0
        shift = (self._endocrine.cortisol * 0.1) - (self._endocrine.dopamine * 0.05)  # type: ignore[type-error]
        return float(shift)

    async def _find_neighbors(self, candidate: CortexSemanticEngram, limit: int) -> list[Any]:
        """Search for nearest neighbors in vector store."""
        if hasattr(self._vs, "search_similar"):
            return await self._vs.search_similar(
                embedding=candidate.embedding,
                tenant_id=candidate.tenant_id,
                limit=limit,
            )
        logger.debug("Vector store lacks search_similar; falling through.")
        return []

    def _evaluate_resonance(
        self,
        candidate: CortexSemanticEngram,
        neighbors: list[Any],
        rho: float,
        topo_boost: float,
    ) -> tuple[CortexSemanticEngram | None, float]:
        """Find the best matching engram above vigilance threshold."""
        best_match: CortexSemanticEngram | None = None
        best_sim = 0.0

        for neighbor in neighbors:
            if type(neighbor).__name__ != "CortexSemanticEngram":
                continue

            # Semantic Similarity
            sim = cosine_similarity(candidate.embedding, neighbor.embedding)

            # Reality hierarchy check: skip resonance if candidate is speculative (< C5)
            # and neighbor is established C5 truth, and contents differ.
            if (
                sim >= 0.80
                and candidate.content.strip().lower() != neighbor.content.strip().lower()
            ):
                cand_speculative = is_less_than_c5(get_confidence_val(candidate))
                neigh_established = not is_less_than_c5(get_confidence_val(neighbor))
                if cand_speculative and neigh_established:
                    # Skip resonance to let it collide in epistemic physics resolution
                    continue

            # Metabolic Modifier: Lower energy engrams are harder to "wake up"
            current_energy = neighbor.energy_level
            metabolic_penalty = (1.0 - current_energy) * 0.05

            effective_sim = sim + topo_boost - metabolic_penalty

            if effective_sim > best_sim:
                best_sim = effective_sim
                best_match = neighbor

        return (best_match if best_sim >= rho else None), best_sim

    async def gate(
        self,
        candidate: CortexSemanticEngram,
        search_limit: int = 8,
        vigilance_override: float | None = None,
        precision_mode: bool = False,
    ) -> tuple[str, CortexSemanticEngram]:
        """Evaluate a candidate engram against existing memory with adaptive vigilance.

        Returns:
            ("resonance", existing_engram) if match found and reinforced.
            ("reset", candidate) if new engram was inserted.
        """
        import time as _time

        # 1. Dynamic Vigilance Adjustment
        rho = vigilance_override or self._rho

        # Endocrine Modulation [v6.2]
        endocrine_shift = self._calculate_endocrine_shift()
        rho = max(0.5, min(0.98, rho + endocrine_shift))

        if precision_mode:
            rho = min(0.98, rho + 0.1)

        # 2. Find Neighbors and Topology Boost
        neighbors = await self._find_neighbors(candidate, search_limit)
        topo_boost = self._calculate_topographic_boost(candidate)

        # 3. Evaluate Resonance
        best_match, best_sim = self._evaluate_resonance(candidate, neighbors, rho, topo_boost)

        if best_match:
            # RESONANCE → Reinforce (LTP)
            boost = self._ltp_boost + (0.05 if precision_mode else 0.0)
            reinforced = best_match.model_copy(
                update={
                    "last_accessed": _time.monotonic(),
                    "energy_level": min(1.0, best_match.energy_level + boost),
                    "entangled_refs": list(set(best_match.entangled_refs) | {candidate.id}),
                }
            )

            if hasattr(self._vs, "upsert"):
                await self._vs.upsert(reinforced)

            logger.info(
                "ART RESONANCE [v6.1]: engram %s reinforced (sim=%.3f, boost=%.3f)",
                best_match.id,
                best_sim,
                topo_boost,
            )
            return ("resonance", reinforced)

        # 4. Epistemic Physics Collision Resolution
        from babylon60.engine.causal.epistemic_physics import EpistemicPhysicsArbiter
        from babylon60.engine.flow.causality_models import Claim, EpistemicStatus, Evidence

        conflict_detected = False
        claims_to_resolve = []

        # Convert candidate to Claim
        candidate_confidence = confidence_to_float(
            candidate.metadata.get("confidence_score") or candidate.confidence
        )
        candidate_claim = Claim(
            id=candidate.id,
            statement=candidate.content,
            evidence_list=[
                Evidence(
                    source="candidate",
                    confidence=candidate_confidence,
                    metadata={
                        "embedding": candidate.embedding,
                        "contradicts": candidate.metadata.get("contradicts")
                        if candidate.metadata
                        else None,
                    },
                )
            ],
        )
        claims_to_resolve.append(candidate_claim)

        # Map neighbors to detect explicit and implicit contradictions
        neighbor_map = {}
        has_c5_collision = False

        for neighbor in neighbors:
            if type(neighbor).__name__ != "CortexSemanticEngram":
                continue

            is_contradictory = False
            cand_contr = candidate.metadata.get("contradicts") if candidate.metadata else None
            neigh_contr = neighbor.metadata.get("contradicts") if neighbor.metadata else None

            if cand_contr == neighbor.id or neigh_contr == candidate.id:
                is_contradictory = True
            else:
                # IMPLICIT COLLISION: speculative fact vs established C5 truth
                sim = cosine_similarity(candidate.embedding, neighbor.embedding)
                # If they are semantically very similar (>80% similarity) but have different text content
                if (
                    sim >= 0.80
                    and candidate.content.strip().lower() != neighbor.content.strip().lower()
                ):
                    cand_speculative = is_less_than_c5(get_confidence_val(candidate))
                    neigh_established = not is_less_than_c5(get_confidence_val(neighbor))
                    if cand_speculative and neigh_established:
                        is_contradictory = True
                        has_c5_collision = True
                        logger.info(
                            "ART GATE: Implicit collision detected between speculative candidate (%s) "
                            "and established C5 neighbor %s (sim=%.3f).",
                            get_confidence_val(candidate),
                            neighbor.id,
                            sim,
                        )

            if is_contradictory:
                conflict_detected = True
                neighbor_confidence = confidence_to_float(
                    neighbor.metadata.get("confidence_score") or neighbor.confidence
                )
                neigh_claim = Claim(
                    id=neighbor.id,
                    statement=neighbor.content,
                    evidence_list=[
                        Evidence(
                            source="neighbor",
                            confidence=neighbor_confidence,
                            metadata={"embedding": neighbor.embedding, "contradicts": neigh_contr},
                        )
                    ],
                )
                claims_to_resolve.append(neigh_claim)
                neighbor_map[neighbor.id] = neighbor

        if conflict_detected:
            logger.info("ART GATE: Epistemic conflict detected. Resolving via physics engine.")
            physics_arbiter = EpistemicPhysicsArbiter(decay_rate=0.01, collision_threshold=rho)
            traces = physics_arbiter.resolve_collisions(claims_to_resolve)

            # Analyze trace of the candidate claim
            candidate_trace = next(t for t in traces if candidate.id in t.trace_steps[0])

            # If candidate collapses or explicitly collided with an established C5 truth, block ingestion
            if candidate_trace.verdict == EpistemicStatus.CONTRADICTED or has_c5_collision:
                logger.warning(
                    "ART GATE: Ingestion blocked. Speculative claim collapsed by established C5 truth."
                )

                # Emitir métrica de telemetría factual
                metrics.inc(
                    "cortex_contradictions_total",
                    labels={"domain": candidate.tenant_id or "unknown"},
                    meta={"candidate_id": candidate.id},
                )

                return ("blocked", candidate)

            # Update neighbors affected by the collision
            for trace in traces:
                matched_neighbor_id = None
                for n_id in neighbor_map:
                    if n_id in trace.trace_steps[0]:
                        matched_neighbor_id = n_id
                        break

                if matched_neighbor_id:
                    n_engram = neighbor_map[matched_neighbor_id]
                    if trace.verdict == EpistemicStatus.CONTRADICTED:
                        logger.info(
                            "ART GATE: Neighbor %s collapsed in physics collision.",
                            matched_neighbor_id,
                        )
                        n_engram = n_engram.model_copy(
                            update={
                                "energy_level": 0.0,
                                "metadata": {**(n_engram.metadata or {}), "status": "contradicted"},
                            }
                        )
                    else:
                        new_energy = max(0.1, trace.truth_score.value)
                        logger.info(
                            "ART GATE: Neighbor %s energy updated to %.4f.",
                            matched_neighbor_id,
                            new_energy,
                        )
                        n_engram = n_engram.model_copy(
                            update={
                                "energy_level": new_energy,
                                "metadata": {
                                    **(n_engram.metadata or {}),
                                    "confidence_score": trace.truth_score.value,
                                },
                            }
                        )
                    if hasattr(self._vs, "upsert"):
                        await self._vs.upsert(n_engram)

        # RESET → Insert new engram category
        if hasattr(self._vs, "upsert"):
            await self._vs.upsert(candidate)

        logger.info(
            "ART RESET [v6.1]: new engram %s created (best_sim=%.3f < ρ=%.2f)",
            candidate.id,
            best_sim,
            rho,
        )
        return ("reset", candidate)
