# [C5-REAL] Exergy-Maximized

from typing import Any

from legacy_research.sica.meta_level import MetaJudgment
from legacy_research.sica.object_level import ObjectLevel, StepOutcome
from legacy_research.sica.strategy import SearchStrategy


class SelfAssessor:
    """Handles confidence assessment and output revision."""

    def __init__(self, object_level: ObjectLevel, strategy: SearchStrategy):
        self._object_level = object_level
        self._strategy = strategy

    def assess_confidence(self, outcome: StepOutcome) -> float:
        """Assess confidence in the result.

        Uses historical performance + current outcome to calibrate.
        """
        base = 0.7 if outcome == StepOutcome.SUCCESS else 0.3

        # Calibrate based on recent trace history
        recent_traces = self._object_level.trace_archive[-10:]
        if recent_traces:
            recent_success_rate = sum(
                1 for t in recent_traces if t.final_outcome == StepOutcome.SUCCESS
            ) / len(recent_traces)
            # Blend base with historical calibration
            calibrated = base * 0.6 + recent_success_rate * 0.4
        else:
            calibrated = base

        # Apply confidence anchoring heuristic if active
        for h in self._strategy.genome.heuristics:
            if h.name == "confidence_anchoring" and h.weight > 0.3:
                calibrated *= 0.7  # Reduce by 30% as prescribed
                break

        return min(1.0, max(0.0, calibrated))

    def revise_output(
        self,
        result: dict[str, Any],
        judgment: MetaJudgment,
    ) -> dict[str, Any]:
        """Revise output to address structural constitutional violations."""
        revised = dict(result)
        revised["_sica_revised"] = True
        revised["_revision_reason"] = judgment.diagnosis

        if judgment.constitutional_verdict:
            for v in judgment.constitutional_verdict.structural_violations:
                revised.setdefault("_constitutional_notes", []).append(
                    f"[{v.principle.id}] {v.explanation}"
                )

        return revised
