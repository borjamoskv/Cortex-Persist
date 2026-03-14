"""Tests for atms.py — ATMS-lite truth maintenance."""

from __future__ import annotations

import pytest

from benchmarks.encb.atms import ATMSLite, AssumptionLabel


class TestAssumptionLabel:
    """Test AssumptionLabel operations."""

    def test_intersects(self):
        l1 = AssumptionLabel(frozenset({"a1", "a2"}))
        l2 = AssumptionLabel(frozenset({"a2", "a3"}))
        assert l1.intersects(l2)

    def test_not_intersects(self):
        l1 = AssumptionLabel(frozenset({"a1"}))
        l2 = AssumptionLabel(frozenset({"a2"}))
        assert not l1.intersects(l2)

    def test_contains_nogood(self):
        l1 = AssumptionLabel(frozenset({"a1", "a2", "a3"}))
        assert l1.contains(frozenset({"a1", "a2"}))

    def test_not_contains_nogood(self):
        l1 = AssumptionLabel(frozenset({"a1"}))
        assert not l1.contains(frozenset({"a1", "a2"}))


class TestATMSLite:
    """Test ATMS-lite operations."""

    def test_valid_belief(self):
        atms = ATMSLite()
        atms.add_justification("b1", frozenset({"a1", "a2"}))
        assert atms.is_valid("b1")

    def test_unknown_belief_invalid(self):
        atms = ATMSLite()
        assert not atms.is_valid("unknown")

    def test_nogood_invalidates(self):
        atms = ATMSLite()
        atms.add_justification("b1", frozenset({"a1", "a2"}))
        atms.add_nogood(frozenset({"a1", "a2"}))
        assert not atms.is_valid("b1")

    def test_partial_nogood_doesnt_invalidate(self):
        atms = ATMSLite()
        atms.add_justification("b1", frozenset({"a1", "a2", "a3"}))
        atms.add_nogood(frozenset({"a4", "a5"}))
        assert atms.is_valid("b1")

    def test_multiple_justifications_one_survives(self):
        atms = ATMSLite()
        atms.add_justification("b1", frozenset({"a1", "a2"}))
        atms.add_justification("b1", frozenset({"a3", "a4"}))
        atms.add_nogood(frozenset({"a1", "a2"}))
        # Second label should still be valid
        assert atms.is_valid("b1")

    def test_all_justifications_killed(self):
        atms = ATMSLite()
        atms.add_justification("b1", frozenset({"a1", "a2"}))
        atms.add_justification("b1", frozenset({"a2", "a3"}))
        atms.add_nogood(frozenset({"a1", "a2"}))
        atms.add_nogood(frozenset({"a2", "a3"}))
        assert not atms.is_valid("b1")

    def test_invalidate_propagation(self):
        atms = ATMSLite()
        atms.add_justification("premise", frozenset({"a1"}))
        atms.add_justification("conclusion", frozenset({"a2"}))
        atms.add_entailment("premise", "conclusion")

        invalidated = atms.invalidate("premise")
        assert "premise" in invalidated
        # conclusion depends on premise
        assert "conclusion" in invalidated

    def test_get_valid_and_invalid(self):
        atms = ATMSLite()
        atms.add_justification("b1", frozenset({"a1"}))
        atms.add_justification("b2", frozenset({"a2"}))
        atms.add_nogood(frozenset({"a2"}))

        valid = atms.get_valid_beliefs()
        invalid = atms.get_invalid_beliefs()
        assert "b1" in valid
        assert "b2" in invalid

    def test_num_properties(self):
        atms = ATMSLite()
        atms.add_justification("b1", frozenset({"a1"}))
        atms.add_justification("b2", frozenset({"a2"}))
        atms.add_nogood(frozenset({"a1", "a2"}))
        assert atms.num_beliefs == 2
        assert atms.num_nogoods == 1
