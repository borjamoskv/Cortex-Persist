"""MOSKV-1 — Tesseract Manifold Convergence Engine."""

from __future__ import annotations

from cortex.manifold.models import DimensionType, WaveState


class ConvergenceEngine:
    """Evaluates the mathematical stability of the Tesseract Manifold."""

    @staticmethod
    def evaluate(state: WaveState) -> bool:
        """Returns True if the manifold has converged and can crystallize."""
        return state.metrics.has_converged()

    @staticmethod
    def calculate_amplification(state: WaveState) -> list[DimensionType]:
        """Returns which dimensions need to be amplified in the next cycle."""
        to_amplify = []
        metrics = state.metrics

        if metrics.entropy_delta > 0:
            to_amplify.append(DimensionType.D4_VALIDATION)

        if metrics.siege_survival_rate < 0.95:
            if DimensionType.D3_CREATION not in to_amplify:
                to_amplify.append(DimensionType.D3_CREATION)
            if DimensionType.D4_VALIDATION not in to_amplify:
                to_amplify.append(DimensionType.D4_VALIDATION)

        if metrics.prediction_accuracy < 0.70:
            to_amplify.append(DimensionType.D1_PERCEPTION)

        if metrics.fitness_score < 0.85 or metrics.intent_drift > 0.10:
            if DimensionType.D2_DECISION not in to_amplify:
                to_amplify.append(DimensionType.D2_DECISION)

        return to_amplify
