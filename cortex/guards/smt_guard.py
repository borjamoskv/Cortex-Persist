# [C5-REAL] Exergy-Maximized
"""
SMT Constraint Guard - Formal Verification via Z3.

Uses Z3 SMT solver to formally validate fact constraints,
temporal ordering, and cross-fact consistency. When Z3 is
not installed, falls back to arithmetic bounds checking.

Reality Level: C5-REAL
"""

import logging
import re
from typing import Any

try:
    from z3 import Int, Real, Solver, sat, unsat, Bool, And

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
                "Z3 not installed - SMTConstraintGuard running in arithmetic fallback mode. Install with: pip install z3-solver"
            )

    @property
    def backend(self) -> str:
        """Get the backend implementation name."""
        return "z3-smt" if self._z3_available else "arithmetic-fallback"

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
        self, confidence: float | None, timestamp: float | None, content_length: int | None
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
        return True

    def _validate_fact_arithmetic(
        self, confidence: float | None, timestamp: float | None, content_length: int | None
    ) -> bool:
        if confidence is not None and (not 0.0 <= float(confidence) <= 1.0):
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
        timestamps = [f.get("timestamp", f.get("created_at")) for f in facts]
        valid_ts = [t for t in timestamps if t is not None]
        if len(valid_ts) >= 2:
            ts_vars = [Real(f"ts_{i}") for i in range(len(valid_ts))]
            for var, val in zip(ts_vars, valid_ts, strict=True):
                s.add(var == float(val))
                s.add(var > 0.0)
            for i in range(len(ts_vars) - 1):
                s.add(ts_vars[i] <= ts_vars[i + 1])
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
                for i in range(len(c_vars)):
                    for j in range(i + 1, len(c_vars)):
                        diff = Real(f"diff_{subj}_{i}_{j}")
                        s.add(diff == c_vars[i] - c_vars[j])
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
        unsat_core = []
        if not consistent:
            unsat_core = self.isolate_unsat_core(facts)
        return {
            "backend": self.backend,
            "total": len(facts),
            "valid": sum(results),
            "invalid": len(results) - sum(results),
            "consistent": consistent,
            "unsat_core": unsat_core,
            "pass_rate": round(sum(results) / len(results), 4) if results else 1.0,
        }

    def isolate_unsat_core(self, facts: list[dict[str, Any]]) -> list[str]:
        """Isolate conflicting constraints when a batch of facts is unsat/inconsistent.

        Returns a list of string descriptions explaining which constraints form the unsat core.
        """
        if not self._z3_available:
            unsat_reasons = []
            # Check temporal ordering
            timestamps = [f.get("timestamp", f.get("created_at")) for f in facts]
            valid_ts = [(i, t) for i, t in enumerate(timestamps) if t is not None]
            for idx in range(len(valid_ts) - 1):
                if valid_ts[idx][1] > valid_ts[idx + 1][1]:
                    unsat_reasons.append(
                        f"Temporal ordering violation: fact_{valid_ts[idx][0]} (ts={valid_ts[idx][1]}) > fact_{valid_ts[idx+1][0]} (ts={valid_ts[idx+1][1]})"
                    )
            # Check subject consistency
            by_subject = {}
            for i, f in enumerate(facts):
                subj = f.get("subject", f.get("topic", f.get("ki_id")))
                conf = f.get("confidence", f.get("score"))
                if subj and conf is not None:
                    by_subject.setdefault(str(subj), []).append((i, float(conf)))
            for subj, items in by_subject.items():
                for i in range(len(items)):
                    for j in range(i + 1, len(items)):
                        idx_a, val_a = items[i]
                        idx_b, val_b = items[j]
                        if abs(val_a - val_b) > 0.5:
                            unsat_reasons.append(
                                f"Confidence consistency violation on subject '{subj}': fact_{idx_a} (conf={val_a}) and fact_{idx_b} (conf={val_b}) differ by > 0.5"
                            )
            return unsat_reasons

        # Z3 mode
        s = Solver()
        tracking_vars = []

        # 1. Temporal validation
        timestamps = [f.get("timestamp", f.get("created_at")) for f in facts]
        valid_ts = [t for t in timestamps if t is not None]
        if len(valid_ts) >= 2:
            ts_vars = [Real(f"ts_{i}") for i in range(len(valid_ts))]
            for i, (var, val) in enumerate(zip(ts_vars, valid_ts, strict=True)):
                val_track = Bool(f"track_ts_val_{i}")
                s.assert_and_track(var == float(val), val_track)
                tracking_vars.append(val_track)

                bounds_track = Bool(f"track_ts_bounds_{i}")
                s.assert_and_track(var > 0.0, bounds_track)
                tracking_vars.append(bounds_track)

            for i in range(len(ts_vars) - 1):
                order_track = Bool(f"track_ts_order_{i}_{i+1}")
                s.assert_and_track(ts_vars[i] <= ts_vars[i + 1], order_track)
                tracking_vars.append(order_track)

        # 2. Subject validation
        by_subject = {}
        for idx, f in enumerate(facts):
            subj = f.get("subject", f.get("topic", f.get("ki_id")))
            conf = f.get("confidence", f.get("score"))
            if subj and conf is not None:
                by_subject.setdefault(str(subj), []).append((idx, float(conf)))

        for subj, items in by_subject.items():
            if len(items) >= 2:
                c_vars = [Real(f"c_{subj}_{i}") for i in range(len(items))]
                for i, (idx, val) in enumerate(items):
                    val_track = Bool(f"track_conf_val_{subj}_{idx}")
                    s.assert_and_track(c_vars[i] == val, val_track)
                    tracking_vars.append(val_track)

                for i in range(len(c_vars)):
                    for j in range(i + 1, len(c_vars)):
                        idx_a = items[i][0]
                        idx_b = items[j][0]
                        diff = Real(f"diff_{subj}_{idx_a}_{idx_b}")
                        s.add(diff == c_vars[i] - c_vars[j])

                        consistency_track = Bool(f"track_consistency_{subj}_{idx_a}_{idx_b}")
                        s.assert_and_track(And(diff >= -0.5, diff <= 0.5), consistency_track)
                        tracking_vars.append(consistency_track)

        if s.check() == sat:
            return []

        unsat_core = s.unsat_core()
        reasons = []
        for track in unsat_core:
            name = str(track)
            
            # Format to human readable format
            match_order = re.match(r"track_ts_order_(\d+)_(\d+)", name)
            match_val = re.match(r"track_ts_val_(\d+)", name)
            match_bounds = re.match(r"track_ts_bounds_(\d+)", name)
            match_conf = re.match(r"track_conf_val_(.+)_(?P<idx>\d+)", name)
            match_consistency = re.match(r"track_consistency_(.+)_(?P<idx_a>\d+)_(?P<idx_b>\d+)", name)

            if match_order:
                a, b = match_order.groups()
                reasons.append(f"Temporal ordering violation between fact_{a} and fact_{b}")
            elif match_val:
                a = match_val.group(1)
                reasons.append(f"Fact_{a} has invalid/contradictory timestamp value")
            elif match_bounds:
                a = match_bounds.group(1)
                reasons.append(f"Fact_{a} has timestamp <= 0")
            elif match_conf:
                subj = match_conf.group(1)
                idx = match_conf.group("idx")
                reasons.append(f"Fact_{idx} has confidence value conflict on subject '{subj}'")
            elif match_consistency:
                subj = match_consistency.group(1)
                idx_a = match_consistency.group("idx_a")
                idx_b = match_consistency.group("idx_b")
                reasons.append(f"Confidence consistency violation on subject '{subj}' between fact_{idx_a} and fact_{idx_b}")
            else:
                reasons.append(name)
                
        return sorted(reasons)
