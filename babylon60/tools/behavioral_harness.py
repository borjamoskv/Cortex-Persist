import hashlib
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

from babylon60.tools.behavioral_matrix import BehavioralAnalyzer, ConversationTurn
from babylon60.tools.blackbox_harness import BlackBoxHarness, SingleResult
from babylon60.tools.coverage_entropy import CoverageAnalyzer
from babylon60.tools.drift_detector import DriftDetector
from babylon60.tools.excitation_batteries import BatteryManager, DifficultyLevel

# Absolute imports of siblings in babylon60.tools
from babylon60.tools.system_identifier import (
    BehavioralStateVector,
    MahalanobisDistanceCalculator,
    SystemIdentifier,
)


@dataclass
class BehavioralProfile:
    model_id: str
    timestamp_iso: str
    coverage_entropy: float
    family_scores: dict[str, dict[str, float]]
    behavioral_dimensions: dict[str, float]
    state_trajectory: list[np.ndarray]  # State vector representation per prompt
    temperament: dict[str, float]
    profile_hash: str


@dataclass
class ComparisonReport:
    dtw_distance: float
    dtw_normalized: float
    dimension_deltas: dict[str, float]
    dominant_differences: list[str]
    similarity_score: float


@dataclass
class DriftReport:
    kl_divergence: float
    symmetric_kl: float
    is_silent_update: bool
    severity: str
    regressed_families: list[str]
    improved_families: list[str]


class BehavioralHarness:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.blackbox = BlackBoxHarness(config)
        self.sys_id = SystemIdentifier()
        self.analyzer = BehavioralAnalyzer()
        self.drift_det = DriftDetector()
        self.battery = BatteryManager()
        self.coverage_anz = CoverageAnalyzer()

    def run_full_profile(
        self, families: Optional[list[str]] = None, difficulty: Optional[DifficultyLevel] = None
    ) -> BehavioralProfile:
        prompts = self.battery.get_battery(families, difficulty)

        results: list[SingleResult] = []
        states: list[BehavioralStateVector] = []
        turns: list[ConversationTurn] = []

        prev_response = None
        for i, p in enumerate(prompts):
            # Run prompt using local blackbox wrapper
            res = self.blackbox.run_prompt(p.prompt_text, p.ground_truth, force_stream=False)
            results.append(res)

            # Extract state vector
            state = self.sys_id.extract_state(
                turn_idx=i,
                response=res.response_text,
                prev_response=prev_response,
                itl=res.ttft_ms if res.ttft_ms is not None else 0.0,
            )
            states.append(state)

            # Save turn for analyzer
            turn = ConversationTurn(
                prompt=p.prompt_text,
                response=res.response_text,
                latency_ms=res.latency_ms,
                completion_tokens=res.completion_tokens if res.completion_tokens is not None else 1,
            )
            turns.append(turn)
            prev_response = res.response_text

        # Compute Coverage Entropy over metrics matrix
        state_vectors = [s.to_vector() for s in states]
        matrix = np.array(state_vectors)
        h_cov = self.coverage_anz.compute_coverage_entropy(matrix)

        # Compute 16 behavioral dimensions (from dimensions 9-16 in behavioral_matrix.py)
        curvature = self.analyzer.analyze_curvature(turns)

        # Format variants for elasticity (simulated mutations of responses)
        responses = [r.response_text for r in results if r.response_text]
        elasticity = self.analyzer.analyze_elasticity(responses[:5] if responses else [""])

        # Robustness against variations
        robustness = self.analyzer.analyze_robustness(
            responses[0] if responses else "", responses[1:4] if len(responses) > 1 else []
        )

        # Compression and expansion sequences
        compression = self.analyzer.analyze_compression(responses[:5] if responses else [""])
        expansion = self.analyzer.analyze_expansion(responses[:5] if responses else [""])

        # Classifications
        last_response = responses[-1] if responses else ""
        contradiction = self.analyzer.classify_contradiction(last_response)
        min_inference = self.analyzer.classify_minimal_inference(last_response)

        # Metacognitive coherence
        meta_coherence = self.analyzer.analyze_metacognitive_coherence(
            responses[0] if responses else "", responses[-1] if len(responses) > 1 else ""
        )

        behavioral_dims = {
            "curvature": curvature,
            "elasticity": elasticity,
            "robustness": robustness,
            "mean_compression_entropy": float(statistics.mean(compression)) if compression else 0.0,
            "mean_expansion_rate": float(statistics.mean(expansion)) if expansion else 0.0,
            "meta_coherence": meta_coherence,
            "contradiction_idx": 1.0 if contradiction == "Conflict Assert" else 0.5,
            "min_inference_idx": 1.0 if min_inference == "Naturalistic Bias (Physics)" else 0.5,
        }

        # Calculate family-level scores
        family_scores = {}
        for fam in families or ["L", "N", "M", "A", "Mc"]:
            fam_results = [r for r, p in zip(results, prompts, strict=False) if p.family == fam]
            success = [r for r in fam_results if r.status_code == 200 and not r.rejected]
            exacts = [r for r in success if r.exact_match is True]

            family_scores[fam] = {
                "success_rate": len(success) / len(fam_results) if fam_results else 0.0,
                "exact_match_rate": len(exacts) / len(success) if success else 0.0,
                "avg_latency_ms": float(statistics.mean([r.latency_ms for r in success]))
                if success
                else 0.0,
            }

        temperament = self.sys_id.profile_temperament(states)

        timestamp = datetime.now(timezone.utc).isoformat()

        # Profile hash for serialization check
        hash_str = f"{self.blackbox.model_id}:{h_cov:.4f}:{len(states)}"
        profile_hash = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()

        return BehavioralProfile(
            model_id=self.blackbox.model_id,
            timestamp_iso=timestamp,
            coverage_entropy=h_cov,
            family_scores=family_scores,
            behavioral_dimensions=behavioral_dims,
            state_trajectory=state_vectors,
            temperament=temperament,
            profile_hash=profile_hash,
        )

    def compare_models(
        self, profile_a: BehavioralProfile, profile_b: BehavioralProfile
    ) -> ComparisonReport:
        # Reconstruct trajectory classes
        traj_a = []
        for i, vec in enumerate(profile_a.state_trajectory):
            traj_a.append(
                BehavioralStateVector(
                    turn_index=i,
                    response_length=int(vec[1] * 1000),
                    lexical_entropy=vec[2],
                    sim_to_context=vec[3],
                    itl_ms=vec[4] * 100,
                    refusal_detected=bool(vec[5]),
                    embedding_vector=vec[6:],
                )
            )

        traj_b = []
        for i, vec in enumerate(profile_b.state_trajectory):
            traj_b.append(
                BehavioralStateVector(
                    turn_index=i,
                    response_length=int(vec[1] * 1000),
                    lexical_entropy=vec[2],
                    sim_to_context=vec[3],
                    itl_ms=vec[4] * 100,
                    refusal_detected=bool(vec[5]),
                    embedding_vector=vec[6:],
                )
            )

        # Calibrate Mahalanobis calculator using combined trajectories
        all_vectors = np.vstack([profile_a.state_trajectory, profile_b.state_trajectory])
        mahalanobis = MahalanobisDistanceCalculator(all_vectors)

        # Compute DTW metrics
        dtw_dist = self.sys_id.compute_trajectory_dtw(traj_a, traj_b, mahalanobis, window=10)
        dtw_norm = self.sys_id.compute_trajectory_dtw_normalized(
            traj_a, traj_b, mahalanobis, window=10
        )

        # Calculate dimension deltas
        dims_a = profile_a.behavioral_dimensions
        dims_b = profile_b.behavioral_dimensions

        deltas = {}
        dominant_diffs = []
        for k in dims_a:
            deltas[k] = float(abs(dims_a[k] - dims_b.get(k, 0.0)))
            if deltas[k] > 0.15:
                dominant_diffs.append(k)

        # Basic similarity metric derived from dimensions and normalized DTW
        sim_val = 1.0 / (1.0 + dtw_norm)

        return ComparisonReport(
            dtw_distance=dtw_dist,
            dtw_normalized=dtw_norm,
            dimension_deltas=deltas,
            dominant_differences=dominant_diffs,
            similarity_score=float(sim_val),
        )

    def detect_drift(self, baseline: BehavioralProfile, current: BehavioralProfile) -> DriftReport:
        snap_a = self.drift_det.capture_snapshot(
            model_id=baseline.model_id, states=baseline.state_trajectory
        )
        snap_b = self.drift_det.capture_snapshot(
            model_id=current.model_id, states=current.state_trajectory
        )

        res = self.drift_det.compute_kl_divergence(snap_a, snap_b)
        alert = self.drift_det.detect_silent_update(snap_a, snap_b)

        # Evaluate performance shifts per family to classify regress/improve
        regressed = []
        improved = []
        for fam in baseline.family_scores:
            if fam in current.family_scores:
                sc_a = baseline.family_scores[fam]["success_rate"]
                sc_b = current.family_scores[fam]["success_rate"]
                if sc_b < sc_a - 0.05:
                    regressed.append(fam)
                elif sc_b > sc_a + 0.05:
                    improved.append(fam)

        return DriftReport(
            kl_divergence=res.kl_forward,
            symmetric_kl=res.symmetric_kl,
            is_silent_update=alert.detected,
            severity=alert.severity,
            regressed_families=regressed,
            improved_families=improved,
        )
