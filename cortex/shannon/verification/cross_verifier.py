# cortex/shannon/verification/cross_verifier.py
# [C5-REAL] Exergy-Maximized

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cortex.runtime.replay.divergence import DivergenceCoordinates, DivergenceMetricEngine
from cortex.shannon.env.trace import EpisodeTrace


class DivergenceType(Enum):
    """
    Taxonomy of execution divergence between internal state (Cortex)
    and external environment (Shannon).
    """

    NONE = "none"

    # 1. Structural Divergence: topological, sequence length, or configuration mismatch.
    STRUCTURAL = "structural"

    # 2. Semantic Divergence: mismatches in actual operations/actions/observations.
    SEMANTIC = "semantic"

    # 3. Partial Divergence: auxiliary fields (rewards, done flags, metadata) mismatch.
    PARTIAL = "partial"


@dataclass(frozen=True)
class DivergenceDetail:
    type: DivergenceType
    step_idx: int | None
    field: str
    expected: Any
    actual: Any
    message: str


@dataclass(frozen=True)
class ExecutionVerdict:
    consistent: bool
    verdict_hash: str
    divergence_type: DivergenceType
    details: list[DivergenceDetail] = field(default_factory=list)
    coordinates: DivergenceCoordinates | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "consistent": self.consistent,
            "verdict_hash": self.verdict_hash,
            "divergence_type": self.divergence_type.value,
            "details": [
                {
                    "type": d.type.value,
                    "step_idx": d.step_idx,
                    "field": d.field,
                    "expected": str(d.expected),
                    "actual": str(d.actual),
                    "message": d.message,
                }
                for d in self.details
            ],
            "coordinates": {
                "structural": self.coordinates.structural,
                "semantic": self.coordinates.semantic,
                "partial": self.coordinates.partial,
                "entropy": self.coordinates.entropy,
                "composite": self.coordinates.composite,
            }
            if self.coordinates
            else None,
        }


def compute_verdict_hash(
    consistent: bool,
    divergence_type: DivergenceType,
    details: list[DivergenceDetail],
    cortex_hash: str,
    shannon_hash: str,
) -> str:
    """Computes a deterministic cryptographic hash representing the verification state."""
    hasher = hashlib.sha256()
    hasher.update(str(consistent).encode())
    hasher.update(divergence_type.value.encode())
    hasher.update(cortex_hash.encode())
    hasher.update(shannon_hash.encode())
    for d in details:
        payload = f"{d.type.value}:{d.step_idx}:{d.field}:{d.expected}:{d.actual}"
        hasher.update(payload.encode())
    return hasher.hexdigest()


class CrossVerifier:
    """
    Cross-System Verifier (A)

    Establishes and enforces a global equivalence relation:
    execution_A ≡ execution_B iff cross_system_verifier(A, B) == consistent

    Guarantees symmetry:
    replay(cortex) == trace(shannon) AND trace(shannon) == replay(cortex)
    """

    @staticmethod
    def extract_shannon_steps(ledger_replay: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Extracts step representations from various ledger/snapshot formats.
        Supports both direct ledger events list and snapshot history with state data.
        """
        extracted = []
        for entry in ledger_replay:
            # Format A: Snapshot dictionary containing shannon steps in data
            if "data" in entry and isinstance(entry["data"], dict):
                sh_steps = entry["data"].get("shannon_steps")
                if isinstance(sh_steps, list):
                    return sh_steps

                # Check for single step properties in snapshot data
                if "step_idx" in entry["data"]:
                    extracted.append(entry["data"])
                    continue

            # Format B: Ledger event tracking step directly
            if entry.get("action") == "SHANNON_STEP" or "step_idx" in entry:
                metadata = entry.get("metadata", entry)
                extracted.append(metadata)

        return extracted

    @classmethod
    def verify_cross_system(
        cls,
        ledger_replay: list[dict[str, Any]],
        episode_trace: EpisodeTrace,
    ) -> ExecutionVerdict:
        """
        Verifies equivalence between internal state evolution and external trace.
        """
        details: list[DivergenceDetail] = []
        cortex_steps = cls.extract_shannon_steps(ledger_replay)

        # Determine base hashes for verdict tracking
        shannon_hash = (
            episode_trace.checksum if episode_trace.verify() else "INVALID_SHANNON_CHECKSUM"
        )

        # Compute a hash of the ledger replay to represent Cortex side state
        cortex_hasher = hashlib.sha256()
        for entry in ledger_replay:
            cortex_hasher.update(json.dumps(entry, sort_keys=True).encode())
        cortex_hash = cortex_hasher.hexdigest()

        # Check for invalid Shannon trace checksum first
        if shannon_hash == "INVALID_SHANNON_CHECKSUM":
            details.append(
                DivergenceDetail(
                    type=DivergenceType.SEMANTIC,
                    step_idx=None,
                    field="checksum",
                    expected=episode_trace.checksum,
                    actual="INVALID",
                    message="EpisodeTrace cryptographic validation failed (checksum mismatch).",
                )
            )
            v_hash = compute_verdict_hash(
                False, DivergenceType.SEMANTIC, details, cortex_hash, shannon_hash
            )
            coordinates = DivergenceCoordinates(
                structural=0.0, semantic=1.0, partial=0.0, entropy=0.0, composite=1.0
            )
            return ExecutionVerdict(
                consistent=False,
                verdict_hash=v_hash,
                divergence_type=DivergenceType.SEMANTIC,
                details=details,
                coordinates=coordinates,
            )

        # 1. Structural Validation (topological, config, and seed metadata)
        # We verify that env settings recorded in Cortex match the environment trace.
        for entry in ledger_replay:
            if "env_id" in entry or (
                "data" in entry and isinstance(entry["data"], dict) and "env_id" in entry["data"]
            ):
                ledger_env_id = entry.get("env_id") or entry["data"].get("env_id")
                if ledger_env_id != episode_trace.env_id:
                    details.append(
                        DivergenceDetail(
                            type=DivergenceType.STRUCTURAL,
                            step_idx=None,
                            field="env_id",
                            expected=episode_trace.env_id,
                            actual=ledger_env_id,
                            message=f"Environment ID mismatch: {episode_trace.env_id} vs {ledger_env_id}",
                        )
                    )

                ledger_seed = entry.get("seed") or entry["data"].get("seed")
                if ledger_seed != episode_trace.seed:
                    details.append(
                        DivergenceDetail(
                            type=DivergenceType.STRUCTURAL,
                            step_idx=None,
                            field="seed",
                            expected=episode_trace.seed,
                            actual=ledger_seed,
                            message=f"Seed mismatch: {episode_trace.seed} vs {ledger_seed}",
                        )
                    )

        # Check length equivalence (symmetry check on cardinality)
        if len(cortex_steps) != len(episode_trace.steps):
            details.append(
                DivergenceDetail(
                    type=DivergenceType.STRUCTURAL,
                    step_idx=None,
                    field="steps_count",
                    expected=len(episode_trace.steps),
                    actual=len(cortex_steps),
                    message=f"Step count mismatch: Shannon has {len(episode_trace.steps)}, Cortex has {len(cortex_steps)}",
                )
            )
            v_hash = compute_verdict_hash(
                False, DivergenceType.STRUCTURAL, details, cortex_hash, shannon_hash
            )
            coordinates = DivergenceMetricEngine.compute_trajectory_distance(
                episode_trace.steps, cortex_steps
            )
            return ExecutionVerdict(
                consistent=False,
                verdict_hash=v_hash,
                divergence_type=DivergenceType.STRUCTURAL,
                details=details,
                coordinates=coordinates,
            )

        # 2. Stepwise & Symmetry Verification
        for idx, (trace_step, cortex_step) in enumerate(
            zip(episode_trace.steps, cortex_steps, strict=False)
        ):
            # Symmetry: Verify sequence indices
            if trace_step.step_idx != idx or int(cortex_step.get("step_idx", -1)) != idx:
                details.append(
                    DivergenceDetail(
                        type=DivergenceType.STRUCTURAL,
                        step_idx=idx,
                        field="step_idx",
                        expected=idx,
                        actual=cortex_step.get("step_idx"),
                        message=f"Out of order step indexing detected at step {idx}",
                    )
                )

            # Semantic Validation: Action/Observation equivalence
            trace_action = trace_step.action_hex.lower()
            cortex_action = str(cortex_step.get("action_hex", "")).lower()
            if trace_action != cortex_action:
                details.append(
                    DivergenceDetail(
                        type=DivergenceType.SEMANTIC,
                        step_idx=idx,
                        field="action_hex",
                        expected=trace_action,
                        actual=cortex_action,
                        message=f"Semantic action mismatch at step {idx}: Trace took {trace_action}, Ledger recorded {cortex_action}",
                    )
                )

            trace_obs = trace_step.observation_hex.lower()
            cortex_obs = str(cortex_step.get("observation_hex", "")).lower()
            if trace_obs != cortex_obs:
                details.append(
                    DivergenceDetail(
                        type=DivergenceType.SEMANTIC,
                        step_idx=idx,
                        field="observation_hex",
                        expected=trace_obs,
                        actual=cortex_obs,
                        message=f"Semantic observation mismatch at step {idx}: Trace saw {trace_obs}, Ledger recorded {cortex_obs}",
                    )
                )

            # Partial Validation: Rewards & Done flags
            trace_reward = float(trace_step.reward)
            cortex_reward = float(cortex_step.get("reward", 0.0))
            if abs(trace_reward - cortex_reward) > 1e-9:
                details.append(
                    DivergenceDetail(
                        type=DivergenceType.PARTIAL,
                        step_idx=idx,
                        field="reward",
                        expected=trace_reward,
                        actual=cortex_reward,
                        message=f"Reward discrepancy at step {idx}: Shannon got {trace_reward}, Cortex got {cortex_reward}",
                    )
                )

            trace_done = bool(trace_step.done)
            cortex_done = bool(cortex_step.get("done", False))
            if trace_done != cortex_done:
                details.append(
                    DivergenceDetail(
                        type=DivergenceType.PARTIAL,
                        step_idx=idx,
                        field="done",
                        expected=trace_done,
                        actual=cortex_done,
                        message=f"Done flag discrepancy at step {idx}: Shannon={trace_done}, Cortex={cortex_done}",
                    )
                )

        # Determine overall verdict consistency
        consistent = len(details) == 0
        if consistent:
            verdict_type = DivergenceType.NONE
        else:
            # Classify overall divergence based on severity (STRUCTURAL > SEMANTIC > PARTIAL)
            types = {d.type for d in details}
            if DivergenceType.STRUCTURAL in types:
                verdict_type = DivergenceType.STRUCTURAL
            elif DivergenceType.SEMANTIC in types:
                verdict_type = DivergenceType.SEMANTIC
            else:
                verdict_type = DivergenceType.PARTIAL

        v_hash = compute_verdict_hash(consistent, verdict_type, details, cortex_hash, shannon_hash)

        # Calculate metric coordinates
        coordinates = DivergenceMetricEngine.compute_trajectory_distance(
            episode_trace.steps, cortex_steps
        )

        return ExecutionVerdict(
            consistent=consistent,
            verdict_hash=v_hash,
            divergence_type=verdict_type,
            details=details,
            coordinates=coordinates,
        )
