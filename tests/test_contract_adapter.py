# [C5-REAL] Exergy-Maximized
"""Contract + Adapter Test Suite.

Tests are organized in three tiers:
    1. Contract-only: Verifies contract.resolve() is deterministic and total.
    2. Adapter-only: Verifies YAML loading and schema validation.
    3. Cross-validation: Verifies adapter.resolve() ≡ contract.resolve().
"""

from __future__ import annotations

from pathlib import Path

import pytest

from legacy_research.router.contract import (
    CognitiveMode,
    InformationState,
    RoutingContext,
    RoutingDecision,
    Severity,
    resolve as contract_resolve,
)

# ═══════════════════════════════════════════════════════════════════════════
# TIER 1: Contract Resolve Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestContractResolve:
    """Verify contract.resolve() is deterministic, total, and gate-ordered."""

    # ─── GATE_ULTRA (severity=CRITICAL or blast_radius >= 3) ──────

    @pytest.mark.parametrize(
        "severity,blast_radius",
        [
            (Severity.CRITICAL, 0),  # severity alone triggers
            (Severity.CRITICAL, 1),
            (Severity.CRITICAL, 5),
            (Severity.LOW, 3),  # blast_radius alone triggers
            (Severity.MEDIUM, 3),
            (Severity.HIGH, 3),
            (Severity.LOW, 10),  # extreme blast_radius
            (Severity.CRITICAL, 3),  # both trigger
        ],
    )
    def test_gate_ultra(self, severity: Severity, blast_radius: int) -> None:
        ctx = RoutingContext(severity=severity, blast_radius=blast_radius)
        decision = contract_resolve(ctx)
        assert decision.mode == CognitiveMode.ULTRA_THINK
        assert decision.gate_id == "GATE_ULTRA"
        assert decision.confidence == 1.0
        assert decision.source == "contract.resolve"

    # ─── GATE_RESEARCH (info_state.has_deficit) ───────────────────

    @pytest.mark.parametrize(
        "exists,reliable,current,expected_deficit_substring",
        [
            (False, True, True, "missing"),
            (True, False, True, "unreliable"),
            (True, True, False, "stale"),
            (False, False, True, "missing"),  # multiple deficits
            (False, False, False, "missing"),  # all deficits
        ],
    )
    def test_gate_research(
        self,
        exists: bool,
        reliable: bool,
        current: bool,
        expected_deficit_substring: str,
    ) -> None:
        ctx = RoutingContext(
            severity=Severity.LOW,
            blast_radius=0,
            info_state=InformationState(
                exists_internally=exists,
                is_reliable=reliable,
                is_current=current,
            ),
        )
        decision = contract_resolve(ctx)
        assert decision.mode == CognitiveMode.DEEP_RESEARCH
        assert decision.gate_id == "GATE_RESEARCH"
        assert expected_deficit_substring in decision.rationale

    # ─── GATE_DEEP (blast_radius == 2 or severity == HIGH) ────────

    @pytest.mark.parametrize(
        "severity,blast_radius",
        [
            (Severity.HIGH, 0),
            (Severity.HIGH, 1),
            (Severity.LOW, 2),
            (Severity.MEDIUM, 2),
            (Severity.HIGH, 2),  # both conditions
        ],
    )
    def test_gate_deep(self, severity: Severity, blast_radius: int) -> None:
        ctx = RoutingContext(severity=severity, blast_radius=blast_radius)
        decision = contract_resolve(ctx)
        assert decision.mode == CognitiveMode.DEEP_THINK
        assert decision.gate_id == "GATE_DEEP"

    # ─── GATE_NORMAL (default fallthrough) ────────────────────────

    @pytest.mark.parametrize(
        "severity,blast_radius",
        [
            (Severity.LOW, 0),
            (Severity.LOW, 1),
            (Severity.MEDIUM, 0),
            (Severity.MEDIUM, 1),
        ],
    )
    def test_gate_normal(self, severity: Severity, blast_radius: int) -> None:
        ctx = RoutingContext(severity=severity, blast_radius=blast_radius)
        decision = contract_resolve(ctx)
        assert decision.mode == CognitiveMode.NORMAL
        assert decision.gate_id == "GATE_NORMAL"

    # ─── Precedence: ULTRA > RESEARCH > DEEP > NORMAL ─────────────

    def test_ultra_beats_research(self) -> None:
        """CRITICAL severity + info deficit → ULTRA wins (gate 1 > gate 2)."""
        ctx = RoutingContext(
            severity=Severity.CRITICAL,
            blast_radius=0,
            info_state=InformationState(exists_internally=False),
        )
        decision = contract_resolve(ctx)
        assert decision.mode == CognitiveMode.ULTRA_THINK
        assert decision.gate_id == "GATE_ULTRA"

    def test_research_beats_deep(self) -> None:
        """Info deficit + HIGH severity → RESEARCH wins (gate 2 > gate 3)."""
        ctx = RoutingContext(
            severity=Severity.HIGH,
            blast_radius=0,
            info_state=InformationState(is_current=False),
        )
        decision = contract_resolve(ctx)
        assert decision.mode == CognitiveMode.DEEP_RESEARCH
        assert decision.gate_id == "GATE_RESEARCH"

    def test_ultra_beats_all(self) -> None:
        """blast_radius >= 3 + info deficit + HIGH severity → ULTRA wins."""
        ctx = RoutingContext(
            severity=Severity.HIGH,
            blast_radius=5,
            info_state=InformationState(exists_internally=False, is_reliable=False),
        )
        decision = contract_resolve(ctx)
        assert decision.mode == CognitiveMode.ULTRA_THINK
        assert decision.gate_id == "GATE_ULTRA"

    # ─── Determinism & Totality ───────────────────────────────────

    def test_idempotent(self) -> None:
        """Same input always produces same output."""
        ctx = RoutingContext(severity=Severity.HIGH, blast_radius=2)
        d1 = contract_resolve(ctx)
        d2 = contract_resolve(ctx)
        assert d1.mode == d2.mode
        assert d1.gate_id == d2.gate_id

    def test_total_function_default_ctx(self) -> None:
        """Default RoutingContext (all defaults) produces a valid decision."""
        decision = contract_resolve(RoutingContext())
        assert isinstance(decision, RoutingDecision)
        assert decision.mode == CognitiveMode.NORMAL

    # ─── Output Schema ────────────────────────────────────────────

    def test_output_schema(self) -> None:
        """RoutingDecision has all required fields."""
        decision = contract_resolve(RoutingContext())
        assert hasattr(decision, "mode")
        assert hasattr(decision, "gate_id")
        assert hasattr(decision, "rationale")
        assert hasattr(decision, "confidence")
        assert hasattr(decision, "source")
        assert 0.0 <= decision.confidence <= 1.0

    # ─── Boundary: blast_radius edge cases ────────────────────────

    def test_blast_radius_boundary_2(self) -> None:
        """blast_radius=2 → DEEP_THINK (not ULTRA)."""
        ctx = RoutingContext(blast_radius=2)
        assert contract_resolve(ctx).mode == CognitiveMode.DEEP_THINK

    def test_blast_radius_boundary_3(self) -> None:
        """blast_radius=3 → ULTRA_THINK (threshold)."""
        ctx = RoutingContext(blast_radius=3)
        assert contract_resolve(ctx).mode == CognitiveMode.ULTRA_THINK


# ═══════════════════════════════════════════════════════════════════════════
# TIER 2: Adapter Loading Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAdapterLoading:
    """Test YAML loading, schema validation, and error handling."""

    def test_load_default_yaml(self) -> None:
        """Default YAML loads without error if it exists."""
        from legacy_research.router.adapter import ExergyConfigAdapter

        yaml_path = (
            Path.home() / ".gemini/config/skills/Exergy-Engine-OMEGA/cognitive_routing_matrix.yaml"
        )
        if not yaml_path.exists():
            pytest.skip("Default YAML not present")

        adapter = ExergyConfigAdapter()
        assert adapter.policy.schema_version == "2026.2"
        assert len(adapter.policy.routing_rules) == 4

    def test_load_missing_yaml_raises(self, tmp_path: Path) -> None:
        """Missing YAML file raises FileNotFoundError."""
        from legacy_research.router.adapter import ExergyConfigAdapter

        with pytest.raises(FileNotFoundError):
            ExergyConfigAdapter(path=tmp_path / "nonexistent.yaml")

    def test_load_invalid_schema_version(self, tmp_path: Path) -> None:
        """Unsupported schema_version raises AdapterSchemaError."""
        from legacy_research.router.adapter import AdapterSchemaError, ExergyConfigAdapter

        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(
            "schema_version: '1.0'\nrouting_rules:\n  - id: X\n    condition: 'x'\n    result: normal\n"
        )
        with pytest.raises(AdapterSchemaError, match="Unsupported schema_version"):
            ExergyConfigAdapter(path=bad_yaml)

    def test_load_missing_rules(self, tmp_path: Path) -> None:
        """Empty routing_rules raises AdapterSchemaError."""
        from legacy_research.router.adapter import AdapterSchemaError, ExergyConfigAdapter

        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("schema_version: '2026.2'\nrouting_rules: []\n")
        with pytest.raises(AdapterSchemaError, match="non-empty list"):
            ExergyConfigAdapter(path=bad_yaml)

    def test_load_invalid_mode(self, tmp_path: Path) -> None:
        """Invalid result mode in rule raises AdapterSchemaError."""
        from legacy_research.router.adapter import AdapterSchemaError, ExergyConfigAdapter

        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(
            "schema_version: '2026.2'\nrouting_rules:\n"
            "  - id: X\n    condition: 'x'\n    result: turbo_mode\n"
        )
        with pytest.raises(AdapterSchemaError, match="not in valid modes"):
            ExergyConfigAdapter(path=bad_yaml)


# ═══════════════════════════════════════════════════════════════════════════
# TIER 3: Cross-Validation (Adapter ≡ Contract)
# ═══════════════════════════════════════════════════════════════════════════


class TestAdapterContractEquivalence:
    """Verify adapter.resolve() produces identical results to contract.resolve().

    This is the critical test tier. If any test here fails,
    it means the YAML policy has drifted from the contract.
    """

    @pytest.fixture
    def adapter(self):
        from legacy_research.router.adapter import ExergyConfigAdapter

        yaml_path = (
            Path.home() / ".gemini/config/skills/Exergy-Engine-OMEGA/cognitive_routing_matrix.yaml"
        )
        if not yaml_path.exists():
            pytest.skip("Default YAML not present")
        return ExergyConfigAdapter(strict=True)

    @pytest.mark.parametrize(
        "severity,blast_radius,info_state",
        [
            # GATE_ULTRA
            (Severity.CRITICAL, 0, InformationState()),
            (Severity.LOW, 3, InformationState()),
            (Severity.LOW, 10, InformationState()),
            (Severity.CRITICAL, 5, InformationState()),
            # GATE_RESEARCH
            (Severity.LOW, 0, InformationState(exists_internally=False)),
            (Severity.LOW, 0, InformationState(is_reliable=False)),
            (Severity.LOW, 0, InformationState(is_current=False)),
            (Severity.LOW, 0, InformationState(False, False, False)),
            # GATE_DEEP
            (Severity.HIGH, 0, InformationState()),
            (Severity.LOW, 2, InformationState()),
            (Severity.HIGH, 2, InformationState()),
            # GATE_NORMAL
            (Severity.LOW, 0, InformationState()),
            (Severity.LOW, 1, InformationState()),
            (Severity.MEDIUM, 0, InformationState()),
            (Severity.MEDIUM, 1, InformationState()),
        ],
    )
    def test_adapter_matches_contract(
        self,
        adapter,
        severity: Severity,
        blast_radius: int,
        info_state: InformationState,
    ) -> None:
        """Adapter resolve must match contract resolve for every gate combination."""
        ctx = RoutingContext(
            severity=severity,
            blast_radius=blast_radius,
            info_state=info_state,
        )
        # adapter.resolve() in strict mode already cross-validates internally.
        # This test ensures no AdapterContractDrift is raised.
        adapter_decision = adapter.resolve(ctx)
        contract_decision = contract_resolve(ctx)

        assert adapter_decision.mode == contract_decision.mode
        assert adapter_decision.gate_id == contract_decision.gate_id

    # ─── Precedence collision: adapter must respect same order ────

    def test_precedence_ultra_over_research(self, adapter) -> None:
        ctx = RoutingContext(
            severity=Severity.CRITICAL,
            info_state=InformationState(exists_internally=False),
        )
        d = adapter.resolve(ctx)
        assert d.mode == CognitiveMode.ULTRA_THINK
        assert d.gate_id == "GATE_ULTRA"

    def test_precedence_research_over_deep(self, adapter) -> None:
        ctx = RoutingContext(
            severity=Severity.HIGH,
            info_state=InformationState(is_current=False),
        )
        d = adapter.resolve(ctx)
        assert d.mode == CognitiveMode.DEEP_RESEARCH
        assert d.gate_id == "GATE_RESEARCH"

    def test_source_is_adapter(self, adapter) -> None:
        """Adapter decisions must identify source as 'adapter'."""
        ctx = RoutingContext()
        d = adapter.resolve(ctx)
        assert d.source == "adapter"
