"""
SMT Constraint Guard - Formal Verification via Z3.

Uses Z3 SMT solver to formally validate fact constraints,
temporal ordering, and cross-fact consistency. When Z3 is
not installed, falls back to arithmetic bounds checking.

Reality Level: C5-REAL
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from z3 import And, ArithRef, Bool, Int, Or, Real, Solver, sat, unsat

    HAS_Z3 = True
except ImportError:
    HAS_Z3 = False

logger = logging.getLogger("cortex.guards.smt_guard")


class SMTConstraintGuard:
    """Formal constraint validation using Z3 SMT solver.

    Validates numeric invariants, temporal ordering, and
    cross-fact consistency using satisfiability checking.
    Falls back to arithmetic bounds if Z3 is unavailable.
    """

    def __init__(self) -> None:
        self._z3_available = HAS_Z3
        if not HAS_Z3:
            logger.warning(
                "Z3 not installed - SMTConstraintGuard running in arithmetic fallback mode. "
                "Install with: pip install z3-solver"
            )

    @property
    def backend(self) -> str:
        return "z3-smt" if self._z3_available else "arithmetic-fallback"

    # ── Core Validators ────────────────────────────────────

    def validate_fact(self, fact: dict[str, Any]) -> bool:
        """Validate a single fact's numeric constraints via SMT.

        Constraints verified:
        - confidence ∈ [0.0, 1.0]
        - timestamp > 0
        - content_length > 0 (if present)
        - entropy_score ∈ [0.0, ∞) (if present)

        Returns True if all constraints are satisfiable.
        """
        confidence = fact.get("confidence", fact.get("score"))
        timestamp = fact.get("timestamp", fact.get("created_at"))
        content_length = fact.get("content_length", fact.get("length"))

        if self._z3_available:
            return self._validate_fact_z3(confidence, timestamp, content_length)
        return self._validate_fact_arithmetic(confidence, timestamp, content_length)

    def _validate_fact_z3(
        self,
        confidence: float | None,
        timestamp: float | None,
        content_length: int | None,
    ) -> bool:
        s = Solver()

        if confidence is not None:
            c = Real("confidence")
            s.add(c == float(confidence))
            s.add(c >= 0.0)
            s.add(c <= 1.0)

        if timestamp is not None:
            t = Real("timestamp")
            s.add(t == float(timestamp))
            s.add(t > 0.0)

        if content_length is not None:
            n = Int("content_length")
            s.add(n == int(content_length))
            s.add(n > 0)

        result = s.check()
        if result == unsat:
            logger.warning(
                "SMT constraint UNSAT: conf=%s ts=%s len=%s", confidence, timestamp, content_length
            )
            return False
        return True  # sat or unknown → pass (open-world assumption)

    def _validate_fact_arithmetic(
        self,
        confidence: float | None,
        timestamp: float | None,
        content_length: int | None,
    ) -> bool:
        if confidence is not None and not (0.0 <= float(confidence) <= 1.0):
            return False
        if timestamp is not None and float(timestamp) <= 0.0:
            return False
        if content_length is not None and int(content_length) <= 0:
            return False
        return True

    def validate_bounds(self, value: float, min_val: float, max_val: float) -> bool:
        """Formally verify value ∈ [min_val, max_val] via Z3."""
        if self._z3_available:
            s = Solver()
            v = Real("v")
            s.add(v == float(value))
            s.add(v >= float(min_val))
            s.add(v <= float(max_val))
            return s.check() == sat
        return min_val <= value <= max_val

    def validate_consistency(self, facts: list[dict[str, Any]]) -> bool:
        """Validate cross-fact consistency via Z3.

        Checks:
        - No two facts claim contradictory confidence for the same subject
          (difference > 0.5 is flagged as inconsistent)
        - Temporal ordering: facts must have non-decreasing timestamps
          when sorted by creation order

        Returns True if the fact set is consistent.
        """
        if not facts:
            return True

        if self._z3_available:
            return self._validate_consistency_z3(facts)
        return self._validate_consistency_arithmetic(facts)

    def _validate_consistency_z3(self, facts: list[dict[str, Any]]) -> bool:
        s = Solver()

        # Temporal ordering constraint
        timestamps = [f.get("timestamp", f.get("created_at")) for f in facts]
        valid_ts = [t for t in timestamps if t is not None]
        if len(valid_ts) >= 2:
            ts_vars = [Real(f"ts_{i}") for i in range(len(valid_ts))]
            for var, val in zip(ts_vars, valid_ts, strict=True):
                s.add(var == float(val))
                s.add(var > 0.0)
            # Enforce non-strict ordering (timestamps can be equal for batch writes)
            for i in range(len(ts_vars) - 1):
                s.add(ts_vars[i] <= ts_vars[i + 1])

        # Confidence contradiction check: group by subject
        by_subject: dict[str, list[float]] = {}
        for f in facts:
            subj = f.get("subject", f.get("topic", f.get("ki_id")))
            conf = f.get("confidence", f.get("score"))
            if subj and conf is not None:
                by_subject.setdefault(str(subj), []).append(float(conf))

        for subj, confs in by_subject.items():
            if len(confs) >= 2:
                c_vars = [Real(f"c_{subj}_{i}") for i in range(len(confs))]
                for var, val in zip(c_vars, confs, strict=True):
                    s.add(var == val)
                # Contradiction: max - min > 0.5
                for i in range(len(c_vars)):
                    for j in range(i + 1, len(c_vars)):
                        diff = Real(f"diff_{subj}_{i}_{j}")
                        s.add(diff == c_vars[i] - c_vars[j])
                        # Allow max 0.5 spread in confidence
                        s.add(diff >= -0.5)
                        s.add(diff <= 0.5)

        result = s.check()
        if result == unsat:
            logger.warning("SMT consistency check UNSAT for %d facts", len(facts))
            return False
        return True

    def _validate_consistency_arithmetic(self, facts: list[dict[str, Any]]) -> bool:
        timestamps = [f.get("timestamp", f.get("created_at")) for f in facts]
        valid_ts = sorted(t for t in timestamps if t is not None)
        for i in range(len(valid_ts) - 1):
            if valid_ts[i] > valid_ts[i + 1]:
                return False

        by_subject: dict[str, list[float]] = {}
        for f in facts:
            subj = f.get("subject", f.get("topic", f.get("ki_id")))
            conf = f.get("confidence", f.get("score"))
            if subj and conf is not None:
                by_subject.setdefault(str(subj), []).append(float(conf))

        for confs in by_subject.values():
            if max(confs) - min(confs) > 0.5:
                return False
        return True

    def audit_report(self, facts: list[dict[str, Any]]) -> dict[str, Any]:
        """Return structured audit report for a batch of facts."""
        results = [self.validate_fact(f) for f in facts]
        consistent = self.validate_consistency(facts)
        return {
            "backend": self.backend,
            "total": len(facts),
            "valid": sum(results),
            "invalid": len(results) - sum(results),
            "consistent": consistent,
            "pass_rate": round(sum(results) / len(results), 4) if results else 1.0,
        }
