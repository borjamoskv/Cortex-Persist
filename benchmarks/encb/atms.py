"""ENCB v2 — ATMS-Lite (Assumption-based Truth Maintenance System).

Layer 3: Truth maintenance. Tracks which assumptions support each belief
and detects/propagates inconsistencies via nogood sets.

Simplified from de Kleer's full ATMS:
- No full label management (too expensive for 10K propositions)
- Tracks assumption → belief mapping and nogood combinations
- Invalidation propagates through a simple entailment graph
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssumptionLabel:
    """A set of assumption IDs that jointly support a belief."""

    assumptions: frozenset[str]

    def intersects(self, other: AssumptionLabel) -> bool:
        """True if these labels share any assumption."""
        return bool(self.assumptions & other.assumptions)

    def contains(self, nogood: frozenset[str]) -> bool:
        """True if this label contains an entire nogood set."""
        return nogood.issubset(self.assumptions)


class ATMSLite:
    """Lightweight assumption-based truth maintenance.

    Maintains three data structures:
    1. justifications: belief_id → set of AssumptionLabels
    2. nogoods: set of frozensets (inconsistent assumption combos)
    3. entailment_graph: belief_id → set of dependent belief_ids

    Usage:
        atms = ATMSLite()
        atms.add_justification("b1", frozenset({"a1", "a2"}))
        atms.add_justification("b2", frozenset({"a2", "a3"}))
        atms.add_nogood(frozenset({"a1", "a3"}))
        assert atms.is_valid("b1")  # True — {a1, a2} doesn't hit nogoods
        atms.add_nogood(frozenset({"a1", "a2"}))
        assert not atms.is_valid("b1")  # False — all labels hit nogoods
    """

    def __init__(self) -> None:
        # belief_id → list of supporting assumption labels
        self._justifications: dict[str, list[AssumptionLabel]] = {}
        # Set of inconsistent assumption combinations
        self._nogoods: set[frozenset[str]] = set()
        # belief_id → belief_ids that depend on it
        self._entails: dict[str, set[str]] = {}
        # belief_id → belief_ids that it depends on
        self._depends_on: dict[str, set[str]] = {}

    def add_justification(
        self,
        belief_id: str,
        assumptions: frozenset[str],
    ) -> None:
        """Register that `assumptions` jointly support `belief_id`."""
        label = AssumptionLabel(assumptions)
        if belief_id not in self._justifications:
            self._justifications[belief_id] = []
        self._justifications[belief_id].append(label)

    def add_entailment(self, premise_id: str, conclusion_id: str) -> None:
        """Register that premise implies conclusion.

        If premise becomes invalid, conclusion may also become invalid.
        """
        if premise_id not in self._entails:
            self._entails[premise_id] = set()
        self._entails[premise_id].add(conclusion_id)

        if conclusion_id not in self._depends_on:
            self._depends_on[conclusion_id] = set()
        self._depends_on[conclusion_id].add(premise_id)

    def add_nogood(self, nogood: frozenset[str]) -> None:
        """Register an inconsistent combination of assumptions."""
        self._nogoods.add(nogood)

    def is_valid(self, belief_id: str) -> bool:
        """Check if a belief has at least one valid justification.

        A justification is valid if its label does NOT contain any nogood.
        A belief with no justifications is invalid.
        """
        labels = self._justifications.get(belief_id, [])
        if not labels:
            return False

        for label in labels:
            # Valid if no nogood is a subset of this label
            nogood_hit = False
            for ng in self._nogoods:
                if label.contains(ng):
                    nogood_hit = True
                    break
            if not nogood_hit:
                return True

        return False

    def invalidate(self, belief_id: str) -> set[str]:
        """Invalidate a belief and propagate through the entailment graph.

        Returns the set of all transitively invalidated belief IDs.
        """
        invalidated: set[str] = set()
        queue = [belief_id]

        while queue:
            current = queue.pop(0)
            if current in invalidated:
                continue
            invalidated.add(current)

            # Remove all justifications for this belief
            self._justifications.pop(current, None)

            # Propagate to dependents
            dependents = self._entails.get(current, set())
            for dep in dependents:
                # Check if dep has any remaining valid justification
                # that doesn't depend on invalidated beliefs
                if not self._has_valid_path(dep, invalidated):
                    queue.append(dep)

        return invalidated

    def _has_valid_path(
        self,
        belief_id: str,
        invalidated: set[str],
    ) -> bool:
        """Check if belief_id has a valid justification not depending on
        any invalidated belief."""
        labels = self._justifications.get(belief_id, [])
        if not labels:
            return False

        # Check if any justification's assumptions are still valid
        for label in labels:
            nogood_hit = any(label.contains(ng) for ng in self._nogoods)
            if not nogood_hit:
                # Also check that no premise in the entailment graph is invalid
                premises = self._depends_on.get(belief_id, set())
                if not premises & invalidated:
                    return True

        return False

    @property
    def num_beliefs(self) -> int:
        return len(self._justifications)

    @property
    def num_nogoods(self) -> int:
        return len(self._nogoods)

    def get_valid_beliefs(self) -> set[str]:
        """Return all belief IDs with at least one valid justification."""
        return {bid for bid in self._justifications if self.is_valid(bid)}

    def get_invalid_beliefs(self) -> set[str]:
        """Return all belief IDs with no valid justification."""
        return {bid for bid in self._justifications if not self.is_valid(bid)}
