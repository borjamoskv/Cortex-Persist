# [C5-REAL] Exergy-Maximized
from babylon60.crypto.hash_registry import cortex_hash
import logging
from collections.abc import Callable

from cortex.engine.flow.causality_models import (
    Claim,
    DecisionTrace,
    EpistemicStatus,
    TruthScore,
    UtilityScore,
)

logger = logging.getLogger("cortex.engine.causal.epistemic_arbiter")


class Constraint:
    def __init__(self, name: str, evaluator: Callable[[Claim], bool], fail_message: str):
        self.name = name
        self.evaluator = evaluator
        self.fail_message = fail_message

    def evaluate(self, claim: Claim) -> bool:
        return self.evaluator(claim)


class EpistemicCompiler:
    """
    Layer 3 Epistemic Arbiter.
    Operates as a Constraint Satisfaction Engine rather than a classifier.
    Never decides what is 'true', only what degree of evidence supports a claim.
    """

    def __init__(self):
        self.constraints: dict[str, Constraint] = {}
        self._register_default_constraints()

    def _register_default_constraints(self):
        self.register_constraint(
            Constraint(
                name="citation_required",
                evaluator=lambda c: len(c.evidence_list) > 0,
                fail_message="Claim lacks any supporting evidence (citation required).",
            )
        )
        self.register_constraint(
            Constraint(
                name="source_agreement_ge_2",
                evaluator=lambda c: len(c.evidence_list) >= 2,
                fail_message="Insufficient source agreement (requires >= 2).",
            )
        )
        self.register_constraint(
            Constraint(
                name="contradiction_false",
                # Dummy implementation: look for 'contradicts' flag in evidence metadata
                evaluator=lambda c: not any(
                    e.metadata.get("contradicts", False) for e in c.evidence_list
                ),
                fail_message="Contradicting evidence detected.",
            )
        )
        self.register_constraint(
            Constraint(
                name="provenance_not_null",
                evaluator=lambda c: all(e.source for e in c.evidence_list),
                fail_message="One or more evidence sources lack provenance.",
            )
        )

    def register_constraint(self, constraint: Constraint):
        self.constraints[constraint.name] = constraint

    def evaluate_claim(self, claim: Claim) -> DecisionTrace:
        trace_steps = []
        trace_steps.append(f"INIT: Evaluating claim {claim.id}")
        
        # 1. Evaluate Constraints
        for constraint_name in claim.constraints:
            if constraint_name not in self.constraints:
                trace_steps.append(f"WARN: Unknown constraint '{constraint_name}' ignored.")
                continue

            constraint = self.constraints[constraint_name]
            trace_steps.append(f"CHECK: {constraint_name}")
            if not constraint.evaluate(claim):
                trace_steps.append(f"FAIL: {constraint.fail_message}")
                return self._finalize_trace(
                    verdict=EpistemicStatus.BLOCKED,
                    trace_steps=trace_steps,
                    truth=0.0,
                    utility=0.0
                )
            trace_steps.append(f"PASS: {constraint_name}")

        # 2. Aggregate Evidence for Truth Score
        if not claim.evidence_list:
            truth = 0.0
            trace_steps.append("EVAL: No evidence provided, truth=0.0")
        else:
            # Simple weighted aggregation for demonstration
            total_weight = sum(e.confidence for e in claim.evidence_list)
            truth = total_weight / len(claim.evidence_list) if claim.evidence_list else 0.0
            trace_steps.append(f"EVAL: Aggregated truth score = {truth:.4f}")

        # 3. Determine utility (Heuristic based on claim statement or context)
        # For now, default to a high baseline if constraints pass, but separated from truth.
        utility = 0.8
        trace_steps.append(f"EVAL: Assessed utility score = {utility:.4f}")

        # 4. Map to High-Res Epistemic Status
        if truth >= 0.9:
            verdict = EpistemicStatus.VERIFIED
        elif truth >= 0.7:
            verdict = EpistemicStatus.SUPPORTED
        elif truth >= 0.4:
            verdict = EpistemicStatus.PARTIALLY_SUPPORTED
        elif truth > 0.0:
            verdict = EpistemicStatus.SPECULATIVE
        else:
            verdict = EpistemicStatus.UNDERDETERMINED

        trace_steps.append(f"DECISION: Verdict mapped to {verdict.value}")

        return self._finalize_trace(
            verdict=verdict,
            trace_steps=trace_steps,
            truth=truth,
            utility=utility
        )

    def _finalize_trace(
        self, 
        verdict: EpistemicStatus, 
        trace_steps: list[str], 
        truth: float, 
        utility: float
    ) -> DecisionTrace:
        # Cryptographic Hash of the decision path
        raw_trace = "\n".join(trace_steps)
        trace_hash = cortex_hash(raw_trace.encode("utf-8"))
        
        return DecisionTrace(
            verdict=verdict,
            trace_steps=trace_steps,
            trace_hash=trace_hash,
            truth_score=TruthScore(value=truth),
            utility_score=UtilityScore(value=utility)
        )
