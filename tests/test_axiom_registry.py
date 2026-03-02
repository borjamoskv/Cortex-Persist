# SPDX-License-Identifier: Apache-2.0
"""Tests for the Canonical Axiom Registry."""

from __future__ import annotations

from cortex.axioms import AXIOM_REGISTRY, AxiomCategory
from cortex.axioms.registry import Axiom, by_category, enforced, get
from cortex.axioms.ttl import FACT_TTL, is_expired, ttl_days


class TestAxiomRegistry:
    """Verify the axiom registry is structurally sound."""

    def test_registry_not_empty(self) -> None:
        assert len(AXIOM_REGISTRY) >= 20, f"Registry degraded: {len(AXIOM_REGISTRY)}"

    def test_all_ids_are_unique(self) -> None:
        ids = list(AXIOM_REGISTRY.keys())
        assert len(ids) == len(set(ids)), "Duplicate axiom IDs detected"

    def test_all_ids_follow_format(self) -> None:
        for ax_id in AXIOM_REGISTRY:
            assert ax_id.startswith("AX-"), f"Invalid ID format: {ax_id}"
            num = ax_id.split("-")[1]
            assert num.isdigit(), f"Non-numeric suffix: {ax_id}"

    def test_constitutional_layer_exists(self) -> None:
        const = by_category(AxiomCategory.CONSTITUTIONAL)
        assert len(const) >= 3, f"Constitutional layer too thin: {len(const)}"

    def test_operational_layer_exists(self) -> None:
        oper = by_category(AxiomCategory.OPERATIONAL)
        assert len(oper) >= 8, f"Operational layer too thin: {len(oper)}"

    def test_aspirational_layer_exists(self) -> None:
        aspir = by_category(AxiomCategory.ASPIRATIONAL)
        assert len(aspir) >= 5, f"Aspirational layer too thin: {len(aspir)}"

    def test_all_axioms_have_names(self) -> None:
        for ax_id, ax in AXIOM_REGISTRY.items():
            assert ax.name, f"{ax_id} has no name"
            assert ax.mandate, f"{ax_id} has no mandate"

    def test_operational_axioms_have_enforcement(self) -> None:
        for ax in by_category(AxiomCategory.OPERATIONAL):
            assert ax.enforcement, f"{ax.id} ({ax.name}) has no enforcement"

    def test_get_existing_axiom(self) -> None:
        ax = get("AX-010")
        assert ax is not None
        assert ax.name == "Zero Trust"

    def test_get_nonexistent_returns_none(self) -> None:
        assert get("AX-999") is None

    def test_enforced_returns_only_gated(self) -> None:
        for ax in enforced():
            assert ax.ci_gate is not None, f"{ax.id} in enforced() but no ci_gate"

    def test_axiom_is_frozen(self) -> None:
        ax = get("AX-010")
        assert ax is not None
        try:
            ax.name = "Mutated"  # type: ignore[misc]
            raise AssertionError("Axiom should be immutable")
        except AttributeError:
            pass  # Correct — frozen dataclass


class TestTTLPolicy:
    """Verify TTL policy for fact types."""

    def test_axioms_are_immortal(self) -> None:
        assert FACT_TTL["axiom"] is None

    def test_decisions_are_immortal(self) -> None:
        assert FACT_TTL["decision"] is None

    def test_ghosts_expire(self) -> None:
        ttl = FACT_TTL["ghost"]
        assert ttl is not None
        assert ttl == 30 * 86_400  # 30 days

    def test_knowledge_expires(self) -> None:
        ttl = FACT_TTL["knowledge"]
        assert ttl is not None
        assert ttl == 180 * 86_400  # 6 months

    def test_is_expired_immortal(self) -> None:
        assert not is_expired("axiom", 999_999_999)

    def test_is_expired_ghost_fresh(self) -> None:
        assert not is_expired("ghost", 86_400)  # 1 day old

    def test_is_expired_ghost_stale(self) -> None:
        assert is_expired("ghost", 31 * 86_400)  # 31 days old

    def test_ttl_days_immortal(self) -> None:
        assert ttl_days("axiom") is None

    def test_ttl_days_ghost(self) -> None:
        assert ttl_days("ghost") == 30

    def test_ttl_days_knowledge(self) -> None:
        assert ttl_days("knowledge") == 180
