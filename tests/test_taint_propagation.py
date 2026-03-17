"""CORTEX — Taint Propagation Test Suite.

Tests the causal DAG taint propagation engine (Axiom Ω₁₃).
Validates tri-state taint, effective confidence recomputation,
multi-parent threshold (50%), and error handling.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CORTEX_TESTING", "1")

import pytest

from cortex.extensions.causality.models import Confidence, FactNode, TaintStatus
from cortex.extensions.causality.taint import (
    downgrade_confidence,
    propagate_taint,
    recompute_effective_confidence,
)

# ── Helper ────────────────────────────────────────────────────────────


def _node(
    fact_id: str,
    confidence: Confidence = Confidence.C5,
    parents: list[str] | None = None,
    children: list[str] | None = None,
) -> FactNode:
    """Create a clean FactNode with sensible defaults."""
    return FactNode(
        fact_id=fact_id,
        confidence=confidence,
        effective_confidence=confidence,
        parents=parents or [],
        children=children or [],
    )


# ── downgrade_confidence ─────────────────────────────────────────────


class TestDowngradeConfidence:
    def test_downgrade_c5_by_2(self) -> None:
        assert downgrade_confidence(Confidence.C5, 2) == Confidence.C3

    def test_downgrade_c3_by_1(self) -> None:
        assert downgrade_confidence(Confidence.C3, 1) == Confidence.C2

    def test_downgrade_clamps_at_c1(self) -> None:
        assert downgrade_confidence(Confidence.C2, 5) == Confidence.C1

    def test_downgrade_by_zero(self) -> None:
        assert downgrade_confidence(Confidence.C4, 0) == Confidence.C4


# ── recompute_effective_confidence ───────────────────────────────────


class TestRecomputeEffectiveConfidence:
    def test_invalidated_node_floors_to_c1(self) -> None:
        node = _node("A")
        node.invalidated = True
        recompute_effective_confidence(node, {})
        assert node.effective_confidence == Confidence.C1

    def test_tainted_node_floors_to_c1(self) -> None:
        node = _node("A")
        node.taint_status = TaintStatus.TAINTED
        recompute_effective_confidence(node, {})
        assert node.effective_confidence == Confidence.C1

    def test_tainted_parent_downgrades_by_2(self) -> None:
        parent = _node("P")
        parent.taint_status = TaintStatus.TAINTED
        child = _node("C", confidence=Confidence.C5, parents=["P"])
        child.taint_status = TaintStatus.SUSPECT

        graph = {"P": parent, "C": child}
        recompute_effective_confidence(child, graph)
        assert child.effective_confidence == Confidence.C3

    def test_suspect_parent_downgrades_by_1(self) -> None:
        parent = _node("P")
        parent.taint_status = TaintStatus.SUSPECT
        child = _node("C", confidence=Confidence.C4, parents=["P"])
        child.taint_status = TaintStatus.SUSPECT

        graph = {"P": parent, "C": child}
        recompute_effective_confidence(child, graph)
        assert child.effective_confidence == Confidence.C3

    def test_all_clean_parents_no_downgrade(self) -> None:
        parent = _node("P")
        child = _node("C", confidence=Confidence.C5, parents=["P"])

        graph = {"P": parent, "C": child}
        recompute_effective_confidence(child, graph)
        assert child.effective_confidence == Confidence.C5


# ── propagate_taint ──────────────────────────────────────────────────


class TestPropagateTaint:
    """Core taint propagation tests with real DAG topologies."""

    def test_linear_chain(self) -> None:
        """A→B→C: invalidate A → B suspect, C suspect."""
        graph = {
            "A": _node("A", children=["B"]),
            "B": _node("B", parents=["A"], children=["C"]),
            "C": _node("C", parents=["B"]),
        }

        touched = propagate_taint("A", graph)

        assert graph["A"].taint_status == TaintStatus.TAINTED
        assert graph["A"].effective_confidence == Confidence.C1
        assert graph["B"].taint_status == TaintStatus.TAINTED  # 1/1 parents tainted
        assert graph["C"].taint_status == TaintStatus.TAINTED  # 1/1 parents tainted
        assert touched == {"A", "B", "C"}

    def test_diamond_dag(self) -> None:
        """A→B, A→C, B→D, C→D: invalidate A → D gets TAINTED (both parents tainted)."""
        graph = {
            "A": _node("A", children=["B", "C"]),
            "B": _node("B", parents=["A"], children=["D"]),
            "C": _node("C", parents=["A"], children=["D"]),
            "D": _node("D", parents=["B", "C"]),
        }

        touched = propagate_taint("A", graph)

        assert graph["D"].taint_status == TaintStatus.TAINTED
        assert graph["D"].effective_confidence == Confidence.C1
        assert len(touched) == 4

    def test_multi_parent_below_threshold(self) -> None:
        """Node with 3 parents, only 1 tainted → stays SUSPECT."""
        graph = {
            "P1": _node("P1", children=["child"]),
            "P2": _node("P2", children=["child"]),
            "P3": _node("P3", children=["child"]),
            "child": _node("child", parents=["P1", "P2", "P3"]),
        }

        propagate_taint("P1", graph)

        # 1/3 = 33% < 50% → SUSPECT, not TAINTED
        assert graph["child"].taint_status == TaintStatus.SUSPECT
        assert graph["child"].effective_confidence != Confidence.C1

    def test_multi_parent_at_threshold(self) -> None:
        """Node with 2 parents, 1 tainted → 50% → escalates to TAINTED."""
        graph = {
            "P1": _node("P1", children=["child"]),
            "P2": _node("P2", children=["child"]),
            "child": _node("child", parents=["P1", "P2"]),
        }

        propagate_taint("P1", graph)

        # 1/2 = 50% ≥ 50% → TAINTED
        assert graph["child"].taint_status == TaintStatus.TAINTED
        assert graph["child"].effective_confidence == Confidence.C1

    def test_unknown_fact_id_raises(self) -> None:
        """Propagating from unknown fact_id → KeyError."""
        with pytest.raises(KeyError, match="Unknown fact_id"):
            propagate_taint("GHOST", {})

    def test_leaf_node_no_children(self) -> None:
        """Invalidating a leaf node touches only itself."""
        graph = {"leaf": _node("leaf")}

        touched = propagate_taint("leaf", graph)

        assert touched == {"leaf"}
        assert graph["leaf"].taint_status == TaintStatus.TAINTED

    def test_already_tainted_node_idempotent(self) -> None:
        """Re-tainting an already tainted node doesn't crash."""
        graph = {
            "A": _node("A", children=["B"]),
            "B": _node("B", parents=["A"]),
        }

        propagate_taint("A", graph)
        # Run again — should be idempotent
        touched = propagate_taint("A", graph)

        assert graph["A"].taint_status == TaintStatus.TAINTED
        assert "A" in touched

    def test_effective_confidence_cascades(self) -> None:
        """C5 nodes degrade properly through the chain."""
        graph = {
            "root": _node("root", confidence=Confidence.C5, children=["mid"]),
            "mid": _node("mid", confidence=Confidence.C5, parents=["root"], children=["leaf"]),
            "leaf": _node("leaf", confidence=Confidence.C4, parents=["mid"]),
        }

        propagate_taint("root", graph)

        assert graph["root"].effective_confidence == Confidence.C1
        # mid: sole parent is tainted → tainted → C1
        assert graph["mid"].effective_confidence == Confidence.C1
        # leaf: sole parent is tainted → tainted → C1
        assert graph["leaf"].effective_confidence == Confidence.C1

    def test_dangling_child_reference_skipped(self) -> None:
        """A child_id not in graph is logged and skipped, not crash."""
        graph = {
            "A": _node("A", children=["MISSING"]),
        }

        # Should not raise
        touched = propagate_taint("A", graph)
        assert touched == {"A"}
