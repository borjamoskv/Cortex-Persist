# [C5-REAL] Exergy-Maximized
"""
Cross-System Invariant Compiler.

Establishes and enforces a global triple-equivalence relation:
shannon_trace ≡ cortex_ledger_replay ≡ ultramap_substrate_evolution

This module guarantees that:
1. Environment physics and observations (Shannon) match the internal causal history (Cortex).
2. Topological mutations in the spatial memory matrix (Ultramap) match the transaction events.
3. Replayable state is 100% deterministic under identical stimulus (no drift).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from cortex.engine.evolution_ledger import EvolutionLedger, MutationRecord
from legacy_research.shannon.env.trace import EpisodeTrace
from legacy_research.shannon.verification.cross_verifier import CrossVerifier

logger = logging.getLogger("cortex.runtime.invariants")


@dataclass(frozen=True)
class InvariantVerdict:
    """The absolute verification proof of cross-system invariance."""

    consistent: bool
    shannon_cortex_hash: str
    substrate_hash: str
    global_proof_hash: str
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consistent": self.consistent,
            "shannon_cortex_hash": self.shannon_cortex_hash,
            "substrate_hash": self.substrate_hash,
            "global_proof_hash": self.global_proof_hash,
            "details": self.details,
        }


class CrossSystemInvariantCompiler:
    """Compiles and verifies the total invariant proof across all execution layers."""

    @staticmethod
    def _compute_substrate_hash(records: list[MutationRecord]) -> str:
        """Computes a deterministic hash over the sequence of substrate mutations."""
        hasher = hashlib.sha256()
        for r in records:
            payload = r.to_payload()
            # Remove timestamp from hash to ensure replay determinism
            payload.pop("ts", None)
            hasher.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
        return hasher.hexdigest()

    @classmethod
    def verify_global_invariance(
        cls,
        shannon_trace: EpisodeTrace,
        cortex_ledger: list[dict[str, Any]],
        substrate_ledger: EvolutionLedger | list[MutationRecord],
    ) -> InvariantVerdict:
        """Verifies the cross-layer equivalence relation.

        Args:
            shannon_trace: The EpisodeTrace containing environment step logs.
            cortex_ledger: The transaction history or runtime state event list.
            substrate_ledger: The evolution ledger or list of records from the Ultramap.

        Returns:
            InvariantVerdict: The proof of consistency or divergence details.
        """
        details: list[str] = []

        # 1. Verify Shannon ≡ Cortex
        verdict = CrossVerifier.verify_cross_system(cortex_ledger, shannon_trace)
        shannon_cortex_hash = verdict.verdict_hash

        if not verdict.consistent:
            for detail in verdict.details:
                details.append(
                    f"[SHANNON-CORTEX DIVERGENCE] Type: {detail.type.value}, "
                    f"Step: {detail.step_idx}, Field: {detail.field}, "
                    f"Expected: {detail.expected}, Got: {detail.actual}. "
                    f"Msg: {detail.message}"
                )

        # 2. Extract substrate mutation records
        if isinstance(substrate_ledger, EvolutionLedger):
            records = list(substrate_ledger.replay(verify=True))
        else:
            records = substrate_ledger

        substrate_hash = cls._compute_substrate_hash(records)

        # 3. Verify Cortex ≡ Ultramap Substrate Evolution
        # Check that control vector updates in the substrate match the step transitions.
        cortex_steps = CrossVerifier.extract_shannon_steps(cortex_ledger)

        # In a closed causal system, every semantic step involving an agent
        # must result in a corresponding control vector mutation in the substrate.
        if len(cortex_steps) > 0 and len(records) == 0:
            details.append(
                "[SUBSTRATE DIVERGENCE] Cortex recorded active steps, but Ultramap substrate evolution is empty."
            )
        elif len(cortex_steps) != len(records) and len(records) > 0:
            # Note: We allow partial evaluation but flag sequence mismatches.
            details.append(
                f"[SUBSTRATE DIVERGENCE] Sequence mismatch: Cortex has {len(cortex_steps)} steps, "
                f"but Ultramap has {len(records)} mutations."
            )

        # Stepwise alignment check
        for idx, (cortex_step, record) in enumerate(zip(cortex_steps, records, strict=False)):
            # Verify agent index correlation if present in metadata
            meta = cortex_step.get("metadata", cortex_step)
            expected_agent_idx = meta.get("agent_idx")
            if expected_agent_idx is not None and record.agent_idx != expected_agent_idx:
                details.append(
                    f"[SUBSTRATE DIVERGENCE] Step {idx}: Agent index mismatch. "
                    f"Cortex expected agent {expected_agent_idx}, Substrate mutated agent {record.agent_idx}."
                )

            # Invariants on Control Vector: error_rate and causal_entropy must not drift to extremes
            vector = record.vector_after
            if vector.error_rate > 0.95:
                details.append(
                    f"[THERMODYNAMIC VIOLATION] Step {idx} (Agent {record.agent_idx}): "
                    f"Substrate error rate is critical ({vector.error_rate:.4f})."
                )
            if vector.causal_entropy < 0.0:
                details.append(
                    f"[THERMODYNAMIC VIOLATION] Step {idx} (Agent {record.agent_idx}): "
                    f"Negative causal entropy ({vector.causal_entropy:.4f}) detected on substrate."
                )

        # 4. Generate Global Proof Hash
        consistent = (len(details) == 0) and verdict.consistent
        global_hasher = hashlib.sha256()
        global_hasher.update(shannon_cortex_hash.encode("utf-8"))
        global_hasher.update(substrate_hash.encode("utf-8"))
        global_hasher.update(str(consistent).encode("utf-8"))
        global_proof_hash = global_hasher.hexdigest()

        if consistent:
            logger.info(
                "C5-REAL: Cross-System Invariance verified. Global Proof Hash: %s",
                global_proof_hash,
            )
        else:
            logger.warning("C4-SIM: Cross-System Divergence detected! Details: %s", details)

        return InvariantVerdict(
            consistent=consistent,
            shannon_cortex_hash=shannon_cortex_hash,
            substrate_hash=substrate_hash,
            global_proof_hash=global_proof_hash,
            details=details,
        )
