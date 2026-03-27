"""Path Validator — Enforces Byzantine Boundaries (Ω1) on reasoning trajectories.

Analyzes CausalEpisodes, generates ReasoningPathFingerprints (Ω14),
and compares them against the user's CognitiveFingerprint to detect drift.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.extensions.fingerprint.models import CognitiveFingerprint
    from cortex.memory.models import CausalEpisode, ReasoningPathFingerprint

from cortex.extensions.fingerprint.extractor import FingerprintExtractor

__all__ = ["PathValidator"]

logger = logging.getLogger("cortex.extensions.fingerprint")


class PathValidator:
    """Validator for agent reasoning paths."""

    def __init__(self, engine: CortexEngine) -> None:
        self._engine = engine

    async def validate_episode(
        self,
        episode: CausalEpisode,
        user_fingerprint: CognitiveFingerprint | None = None,
    ) -> CausalEpisode:
        """Analyze an episode's reasoning path and enforce Byzantine boundaries.

        Args:
            episode: The CausalEpisode to validate.
            user_fingerprint: Optional user fingerprint. If None, it will be extracted.

        Returns:
            The episode with updated fingerprint and byzantine_status.
        """
        if user_fingerprint is None:
            user_fingerprint = await FingerprintExtractor.extract(self._engine)

        # 1. Generate ReasoningPathFingerprint
        path_fp = await self._generate_path_fingerprint(episode)
        episode.fingerprint = path_fp

        # 2. Compare with User Fingerprint (Cognitive Prior)
        drift = self._calculate_drift(path_fp, user_fingerprint)
        path_fp.drift_score = drift

        # 3. Determine Byzantine Status
        # Thresholds based on Ω1: "No confíes en lo que brilla. Confía en lo que compila."
        # In the context of reasoning, "compiling" means matching the structural
        # invariants of the user's own cognitive patterns.
        if drift > 0.7:  # Severe mismatch
            episode.byzantine_status = "faulty"
            logger.warning(
                "Byzantine fault detected in episode %s: drift=%.2f", episode.episode_id, drift
            )
        elif drift > 0.4:  # Significant drift
            episode.byzantine_status = "drifted"
            logger.info(
                "Cognitive drift detected in episode %s: drift=%.2f", episode.episode_id, drift
            )
        else:
            episode.byzantine_status = "valid"

        return episode

    async def _generate_path_fingerprint(self, episode: CausalEpisode) -> ReasoningPathFingerprint:
        """Extract the structural and logical 'shape' of the causal episode."""
        from cortex.memory.models import ReasoningPathFingerprint

        # In a real implementation, we'd traverse the actual fact DAG.
        # For now, we use the episode's metadata as a proxy for the path shape.

        # Heuristic: branching factor = fact_count / max_depth (if linear, 1.0)
        branching = episode.fact_count / max(episode.depth, 1)

        # Intent stability: inverse of fact_type variety in the episode
        # (Placeholder: constant for now, should scan fact types in episode)
        stability = 0.9

        # Structural Hash: hash of (fact_ids, positions, types)
        raw_struct = f"{episode.episode_id}:{episode.fact_count}:{episode.depth}"
        struct_hash = hashlib.sha256(raw_struct.encode()).hexdigest()[:16]

        return ReasoningPathFingerprint(
            causal_depth=episode.depth,
            branching_factor=round(branching, 2),
            intent_stability=stability,
            structural_hash=struct_hash,
            confidence_profile={"avg": 0.8}  # TODO: scan actual facts
        )

    @staticmethod
    def _calculate_drift(
        path_fp: ReasoningPathFingerprint,
        user_fp: CognitiveFingerprint,
    ) -> float:
        """Calculate deviation score [0.0 - 1.0] between agent path and user prior."""
        # Mapping Reasoning dimensions to User Pattern dimensions
        # Example: high branching factor (agent) vs user's synthesis_drive

        diff = 0.0

        # 1. Synthesis/Branching alignment
        # If user is an 'executor' (low synthesis) but agent path is hyper-branched
        diff += abs(path_fp.branching_factor / 5.0 - user_fp.pattern.synthesis_drive)

        # 2. Depth alignment
        # If user prefers concise facts but agent path is extremely deep
        diff += abs(path_fp.causal_depth / 20.0 - user_fp.pattern.depth_preference)

        # 3. Intent stability
        # Lower stability (chaotic reasoning) increases drift score
        diff += (1.0 - path_fp.intent_stability)

        return min(1.0, diff / 3.0)
