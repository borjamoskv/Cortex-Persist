# [C5-REAL] Exergy-Maximized
"""Tests for cortex.guards.saga_contract — SAGA-1 Write-Path Contract."""

import pytest

from cortex.guards.saga_contract import SagaWriteProposal, SagaValidationError


class TestSagaWriteProposal:
    """Structural validation of the SAGA-1 Write-Path Contract."""

    def _valid_kwargs(self, **overrides):
        base = {
            "tenant_id": "test_tenant",
            "project": "test_project",
            "content": "A valid fact for persistence.",
            "fact_type": "knowledge",
            "confidence": "C5",
        }
        base.update(overrides)
        return base

    # ── Happy Path ────────────────────────────────────────────────────

    def test_valid_proposal_creates_successfully(self):
        p = SagaWriteProposal(**self._valid_kwargs())
        assert p.tenant_id == "test_tenant"
        assert p.project == "test_project"
        assert p.fact_type == "knowledge"
        assert p.confidence == "C5"

    def test_valid_proposal_with_all_fields(self):
        p = SagaWriteProposal(
            **self._valid_kwargs(
                tags=["security", "hardening"],
                source="cli",
                metadata={"cortex_taint": "taint:agent:session:2026:nonce:sig"},
                parent_decision_id=42,
            )
        )
        assert p.tags == ["security", "hardening"]
        assert p.source == "cli"
        assert p.parent_decision_id == 42

    def test_to_insert_kwargs(self):
        p = SagaWriteProposal(**self._valid_kwargs())
        kw = p.to_insert_kwargs()
        assert kw["tenant_id"] == "test_tenant"
        assert kw["project"] == "test_project"
        assert kw["content"] == "A valid fact for persistence."
        assert kw["fact_type"] == "knowledge"
        assert kw["confidence"] == "C5"
        assert kw["ts"] is None
        assert kw["tx_id"] is None

    def test_frozen_immutability(self):
        p = SagaWriteProposal(**self._valid_kwargs())
        with pytest.raises(Exception):
            p.tenant_id = "mutated"  # type: ignore[misc]

    # ── Tenant ID Validation ──────────────────────────────────────────

    def test_empty_tenant_id_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(tenant_id=""))

    def test_tenant_id_path_traversal_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(tenant_id="../etc/passwd"))

    def test_tenant_id_null_byte_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(tenant_id="tenant\x00evil"))

    def test_tenant_id_semicolon_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(tenant_id="tenant;DROP TABLE"))

    # ── Content Validation ────────────────────────────────────────────

    def test_empty_content_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(content=""))

    def test_whitespace_only_content_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(content="   "))

    def test_oversized_content_rejected(self):
        huge = "X" * (1_048_577)  # 1MB + 1 byte
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(content=huge))

    def test_max_size_content_accepted(self):
        # Exactly 1MB should pass
        exact = "X" * 1_048_576
        p = SagaWriteProposal(**self._valid_kwargs(content=exact))
        assert len(p.content) == 1_048_576

    # ── Confidence Validation ─────────────────────────────────────────

    def test_valid_confidence_levels(self):
        for level in ["C1", "C2", "C3", "C4", "C5", "C5-REAL", "C3-SIM"]:
            p = SagaWriteProposal(**self._valid_kwargs(confidence=level))
            assert p.confidence == level

    def test_invalid_confidence_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(confidence="HIGH"))

    def test_confidence_c0_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(confidence="C0"))

    def test_confidence_c6_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(confidence="C6"))

    # ── Fact Type Validation ──────────────────────────────────────────

    def test_valid_fact_types(self):
        for ft in [
            "knowledge",
            "decision",
            "error",
            "observation",
            "ghost",
            "pattern",
            "bridge",
            "diamond",
            "telemetry_batch",
        ]:
            p = SagaWriteProposal(**self._valid_kwargs(fact_type=ft))
            assert p.fact_type == ft

    def test_unknown_fact_type_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(fact_type="malicious_type"))

    # ── Tags Validation ───────────────────────────────────────────────

    def test_excessive_tags_rejected(self):
        tags = [f"tag_{i}" for i in range(51)]
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(tags=tags))

    def test_oversized_tag_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(tags=["X" * 129]))

    def test_50_tags_accepted(self):
        tags = [f"tag_{i}" for i in range(50)]
        p = SagaWriteProposal(**self._valid_kwargs(tags=tags))
        assert len(p.tags) == 50

    # ── Taint Token Resolution ────────────────────────────────────────

    def test_resolve_taint_token_cortex_taint(self):
        p = SagaWriteProposal(**self._valid_kwargs(metadata={"cortex_taint": "taint:a:s:t:n:sig"}))
        assert p.resolve_taint_token() == "taint:a:s:t:n:sig"

    def test_resolve_taint_token_uppercase_hyphen(self):
        p = SagaWriteProposal(**self._valid_kwargs(metadata={"CORTEX-TAINT": "taint:a:s:t:n:sig"}))
        assert p.resolve_taint_token() == "taint:a:s:t:n:sig"

    def test_resolve_taint_token_lowercase_hyphen(self):
        p = SagaWriteProposal(**self._valid_kwargs(metadata={"cortex-taint": "taint:a:s:t:n:sig"}))
        assert p.resolve_taint_token() == "taint:a:s:t:n:sig"

    def test_resolve_taint_token_uppercase_underscore(self):
        p = SagaWriteProposal(**self._valid_kwargs(metadata={"CORTEX_TAINT": "taint:a:s:t:n:sig"}))
        assert p.resolve_taint_token() == "taint:a:s:t:n:sig"

    def test_resolve_taint_token_missing(self):
        p = SagaWriteProposal(**self._valid_kwargs(metadata={}))
        assert p.resolve_taint_token() is None

    def test_resolve_taint_priority_order(self):
        """CORTEX-TAINT (hyphen-uppercase) takes priority over cortex_taint."""
        p = SagaWriteProposal(
            **self._valid_kwargs(
                metadata={
                    "cortex_taint": "low_priority",
                    "CORTEX-TAINT": "high_priority",
                }
            )
        )
        assert p.resolve_taint_token() == "high_priority"

    # ── Extra Fields Forbidden ────────────────────────────────────────

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            SagaWriteProposal(**self._valid_kwargs(rogue_field="injected"))
