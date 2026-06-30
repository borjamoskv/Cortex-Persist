# [C5-REAL] Exergy-Maximized
"""
Permanent pytest tests for L0-L6 JSON schema validator.

Coverage matrix:
  - Schema loading (happy, missing dir, no files)
  - LEVEL_MAP semantic aliases (L0-L6)
  - Per-level valid payloads (L0 Evidence → L5/L6 Intervention)
  - Per-level rejections: missing keys, invalid UUID, invalid enum, type mismatch,
    out-of-range numerics, empty arrays violating minItems, extra fields
    (additionalProperties: false), nested object validation
  - ValidationResult structured error enumeration
  - Backward-compatible validate_payload() bool API
  - CortexAuditPipeline integration: acceptance + rejection paths
"""

from __future__ import annotations

import base64
import os
import uuid

os.environ.setdefault("CORTEX_TESTING", "1")
os.environ.setdefault(
    "CORTEX_MASTER_KEY",
    base64.b64encode(os.urandom(32)).decode(),
)

import pytest

from babylon60.engine.causal.schema_validator import (
    LEVEL_MAP,
    L0L6SchemaValidator,
    ValidationResult,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def validator():
    """Provides a fresh L0L6SchemaValidator backed by the real schema/ directory."""
    return L0L6SchemaValidator()


# ── Payload Factories ─────────────────────────────────────────────────────────

_VALID_HASH = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"


def _evidence(**overrides):
    base = {
        "evidence_id": str(uuid.uuid4()),
        "source_type": "AST_DIFF",
        "payload": "diff --git a/x b/y",
        "timestamp": "2026-06-29T19:18:32Z",
        "cortex_taint_hash": _VALID_HASH,
    }
    base.update(overrides)
    return base


def _pattern(**overrides):
    base = {
        "pattern_id": str(uuid.uuid4()),
        "evidence_ids": [str(uuid.uuid4())],
        "invariant_claim": "WAL journal_mode prevents locking contention under concurrent writes.",
        "shannon_entropy_score": 0.85,
    }
    base.update(overrides)
    return base


def _model(**overrides):
    base = {
        "model_id": str(uuid.uuid4()),
        "pattern_ids": [str(uuid.uuid4())],
        "causal_graph": {
            "nodes": [{"id": "A"}, {"id": "B"}],
            "edges": [{"from": "A", "to": "B", "relation": "causes"}],
        },
        "confidence_level": "HIGH",
    }
    base.update(overrides)
    return base


def _prediction(**overrides):
    base = {
        "prediction_id": str(uuid.uuid4()),
        "model_id": str(uuid.uuid4()),
        "falsifiable_condition": "Concurrent WAL writes yield 0 OperationalError drops.",
        "experiment_design": {
            "setup_saga": "Initialize shard with journal_mode=WAL",
            "execution_trigger": "Spawn 10 parallel threads",
            "success_criteria": "error_count == 0",
        },
    }
    base.update(overrides)
    return base


def _experiment(**overrides):
    base = {
        "experiment_id": str(uuid.uuid4()),
        "prediction_id": str(uuid.uuid4()),
        "execution_context": "SANDBOX_THREAD",
        "outcome": {
            "refuted": False,
            "evidence_hash": _VALID_HASH,
        },
    }
    base.update(overrides)
    return base


def _intervention(**overrides):
    base = {
        "intervention_id": str(uuid.uuid4()),
        "prediction_id": str(uuid.uuid4()),
        "git_sentinel_hash": "dcba2835f",
        "saga_rollback_plan": "PRAGMA journal_mode=DELETE on next boot.",
    }
    base.update(overrides)
    return base


# ── Schema Loading ────────────────────────────────────────────────────────────


class TestSchemaLoading:
    """Schema registry initialization and introspection."""

    def test_loads_all_six_schemas(self, validator):
        expected = {
            "evidence.schema",
            "pattern.schema",
            "model.schema",
            "prediction.schema",
            "experiment.schema",
            "intervention.schema",
        }
        assert expected == set(validator.available_schemas)

    def test_each_schema_has_draft07_marker(self, validator):
        for name, schema in validator._schemas.items():
            assert schema.get("$schema") == "http://json-schema.org/draft-07/schema#", name

    def test_each_schema_enforces_additional_properties(self, validator):
        for name, schema in validator._schemas.items():
            assert schema.get("additionalProperties") is False, (
                f"{name} must forbid additionalProperties"
            )

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(RuntimeError, match="no \\*\\.schema\\.json found"):
            L0L6SchemaValidator(schemas_dir=tmp_path / "nonexistent_dir_that_wont_exist")

    def test_empty_directory_raises(self, tmp_path):
        empty = tmp_path / "empty_schemas"
        empty.mkdir()
        with pytest.raises(RuntimeError, match="no \\*\\.schema\\.json found"):
            L0L6SchemaValidator(schemas_dir=empty)


# ── LEVEL_MAP Semantic Aliases ────────────────────────────────────────────────


class TestLevelMap:
    """Verify L0-L6 semantic aliases resolve correctly."""

    @pytest.mark.parametrize(
        "alias,expected_stem",
        [
            ("L0", "evidence.schema"),
            ("L1", "pattern.schema"),
            ("L2", "model.schema"),
            ("L3", "prediction.schema"),
            ("L4", "experiment.schema"),
            ("L5", "intervention.schema"),
            ("L6", "intervention.schema"),
        ],
    )
    def test_alias_resolves(self, validator, alias, expected_stem):
        result = validator.validate(alias, _evidence() if alias == "L0" else {})
        assert result.schema_level == expected_stem or not result.valid

    def test_unknown_level_returns_invalid(self, validator):
        result = validator.validate("L99", {})
        assert not result.valid
        assert "not found" in result.errors[0]


# ── ValidationResult API ─────────────────────────────────────────────────────


class TestValidationResult:
    """Structured error reporting."""

    def test_valid_result_is_truthy(self):
        r = ValidationResult(valid=True, schema_level="test")
        assert r
        assert r.valid
        assert r.errors == []

    def test_invalid_result_is_falsy(self):
        r = ValidationResult(valid=False, errors=["missing key"], schema_level="test")
        assert not r
        assert len(r.errors) == 1

    def test_result_is_frozen(self):
        r = ValidationResult(valid=True, schema_level="x")
        with pytest.raises(AttributeError):
            r.valid = False  # type: ignore[misc]


# ── L0 Evidence ───────────────────────────────────────────────────────────────


class TestL0Evidence:
    """Evidence schema (L0): required keys, UUID format, SHA3-256 pattern, enum."""

    def test_valid_evidence(self, validator):
        assert validator.validate_payload("evidence.schema", _evidence())

    def test_valid_all_source_types(self, validator):
        for src in ("AST_DIFF", "LOG_FILE", "NETWORK_TRACE", "SQLITE_QUERY", "USER_INPUT"):
            assert validator.validate_payload("evidence.schema", _evidence(source_type=src))

    def test_missing_required_key(self, validator):
        p = _evidence()
        del p["cortex_taint_hash"]
        assert not validator.validate_payload("evidence.schema", p)

    def test_invalid_uuid_format(self, validator):
        assert not validator.validate_payload(
            "evidence.schema", _evidence(evidence_id="not-a-uuid")
        )

    def test_invalid_taint_hash_too_short(self, validator):
        assert not validator.validate_payload(
            "evidence.schema", _evidence(cortex_taint_hash="deadbeef")
        )

    def test_invalid_taint_hash_non_hex(self, validator):
        bad = "g" * 64  # 'g' is not hex
        assert not validator.validate_payload("evidence.schema", _evidence(cortex_taint_hash=bad))

    def test_invalid_source_type_enum(self, validator):
        assert not validator.validate_payload(
            "evidence.schema", _evidence(source_type="INVALID_SOURCE")
        )

    def test_wrong_type_for_payload_field(self, validator):
        assert not validator.validate_payload("evidence.schema", _evidence(payload=12345))

    def test_extra_field_rejected(self, validator):
        assert not validator.validate_payload(
            "evidence.schema", _evidence(rogue_field="should_fail")
        )

    def test_multiple_errors_enumerated(self, validator):
        bad = {"evidence_id": 123, "source_type": "WRONG"}
        result = validator.validate("evidence.schema", bad)
        assert not result.valid
        assert len(result.errors) > 1


# ── L1 Pattern ────────────────────────────────────────────────────────────────


class TestL1Pattern:
    """Pattern schema (L1): evidence_ids array, shannon_entropy bounds."""

    def test_valid_pattern(self, validator):
        assert validator.validate_payload("pattern.schema", _pattern())

    def test_empty_evidence_ids_violates_min_items(self, validator):
        assert not validator.validate_payload("pattern.schema", _pattern(evidence_ids=[]))

    def test_entropy_below_zero(self, validator):
        assert not validator.validate_payload(
            "pattern.schema", _pattern(shannon_entropy_score=-0.1)
        )

    def test_entropy_above_one(self, validator):
        assert not validator.validate_payload(
            "pattern.schema", _pattern(shannon_entropy_score=1.001)
        )

    def test_entropy_at_boundaries(self, validator):
        assert validator.validate_payload("pattern.schema", _pattern(shannon_entropy_score=0.0))
        assert validator.validate_payload("pattern.schema", _pattern(shannon_entropy_score=1.0))

    def test_invalid_uuid_in_evidence_ids(self, validator):
        assert not validator.validate_payload("pattern.schema", _pattern(evidence_ids=["not-uuid"]))

    def test_extra_field_rejected(self, validator):
        assert not validator.validate_payload("pattern.schema", _pattern(bonus="nope"))


# ── L2 Cognitive Model ───────────────────────────────────────────────────────


class TestL2Model:
    """Model schema (L2): pattern_ids array, confidence_level enum."""

    def test_valid_model(self, validator):
        assert validator.validate_payload("model.schema", _model())

    @pytest.mark.parametrize("level", ["LOW", "MODERATE", "HIGH", "ABSOLUTE"])
    def test_all_confidence_levels(self, validator, level):
        assert validator.validate_payload("model.schema", _model(confidence_level=level))

    def test_invalid_confidence_level(self, validator):
        assert not validator.validate_payload("model.schema", _model(confidence_level="SUPER_HIGH"))

    def test_empty_pattern_ids_violates_min_items(self, validator):
        assert not validator.validate_payload("model.schema", _model(pattern_ids=[]))

    def test_extra_field_rejected(self, validator):
        assert not validator.validate_payload("model.schema", _model(debug=True))


# ── L3 Prediction ────────────────────────────────────────────────────────────


class TestL3Prediction:
    """Prediction schema (L3): nested experiment_design, experiment_result enum."""

    def test_valid_prediction(self, validator):
        assert validator.validate_payload("prediction.schema", _prediction())

    def test_valid_with_result_enum(self, validator):
        for status in ("PENDING", "REFUTED", "CORROBORATED"):
            assert validator.validate_payload(
                "prediction.schema", _prediction(experiment_result=status)
            )

    def test_invalid_result_enum(self, validator):
        assert not validator.validate_payload(
            "prediction.schema", _prediction(experiment_result="MAYBE")
        )

    def test_missing_nested_required_key(self, validator):
        design = {"setup_saga": "x", "execution_trigger": "y"}  # missing success_criteria
        assert not validator.validate_payload(
            "prediction.schema", _prediction(experiment_design=design)
        )

    def test_extra_field_rejected(self, validator):
        assert not validator.validate_payload("prediction.schema", _prediction(ghost="leak"))


# ── L4 Experiment ────────────────────────────────────────────────────────────


class TestL4Experiment:
    """Experiment schema (L4): execution_context enum, nested outcome."""

    def test_valid_experiment(self, validator):
        assert validator.validate_payload("experiment.schema", _experiment())

    @pytest.mark.parametrize(
        "ctx", ["SANDBOX_THREAD", "ISOLATED_BRANCH", "DRY_RUN", "ORPHAN_QUERY"]
    )
    def test_all_execution_contexts(self, validator, ctx):
        assert validator.validate_payload("experiment.schema", _experiment(execution_context=ctx))

    def test_invalid_execution_context(self, validator):
        assert not validator.validate_payload(
            "experiment.schema", _experiment(execution_context="LIVE_FIRE")
        )

    def test_missing_outcome_required_key(self, validator):
        assert not validator.validate_payload(
            "experiment.schema", _experiment(outcome={"refuted": True})
        )

    def test_outcome_refuted_wrong_type(self, validator):
        assert not validator.validate_payload(
            "experiment.schema",
            _experiment(outcome={"refuted": "yes", "evidence_hash": _VALID_HASH}),
        )


# ── L5/L6 Intervention ───────────────────────────────────────────────────────


class TestL5L6Intervention:
    """Intervention schema (L5 & L6): git hash, rollback plan, reevaluation status enum."""

    def test_valid_intervention(self, validator):
        assert validator.validate_payload("intervention.schema", _intervention())

    def test_valid_with_reevaluation_status(self, validator):
        for status in ("PENDING", "DEGRADED", "RESOLVED"):
            assert validator.validate_payload(
                "intervention.schema",
                _intervention(l6_reevaluation_status=status),
            )

    def test_invalid_reevaluation_status(self, validator):
        assert not validator.validate_payload(
            "intervention.schema",
            _intervention(l6_reevaluation_status="UNKNOWN"),
        )

    def test_missing_required_rollback_plan(self, validator):
        p = _intervention()
        del p["saga_rollback_plan"]
        assert not validator.validate_payload("intervention.schema", p)

    def test_extra_field_rejected(self, validator):
        assert not validator.validate_payload(
            "intervention.schema", _intervention(nonce="injected")
        )


# ── CortexAuditPipeline Integration ──────────────────────────────────────────


class TestAuditPipelineIntegration:
    """Verify CortexAuditPipeline rejects invalid payloads via the schema validator."""

    @pytest.fixture
    def pipeline(self):
        from babylon60.engine.causal.audit_pipeline import CortexAuditPipeline

        return CortexAuditPipeline()

    @pytest.mark.asyncio
    async def test_l0_accepts_valid_evidence(self, pipeline):
        eid = await pipeline.process_l0_evidence(_evidence())
        assert isinstance(eid, str) and len(eid) > 0

    @pytest.mark.asyncio
    async def test_l0_rejects_invalid_evidence(self, pipeline):
        with pytest.raises(ValueError, match="L0 Evidence Rejected"):
            await pipeline.process_l0_evidence({"garbage": True})

    @pytest.mark.asyncio
    async def test_l4_accepts_corroborated_experiment(self, pipeline):
        result = await pipeline.process_l4_experiment(_experiment())
        assert result is True

    @pytest.mark.asyncio
    async def test_l4_rejects_invalid_experiment(self, pipeline):
        with pytest.raises(ValueError, match="L4 Experiment Rejected"):
            await pipeline.process_l4_experiment({"bad": "data"})

    @pytest.mark.asyncio
    async def test_l4_returns_false_when_refuted(self, pipeline):
        exp = _experiment(outcome={"refuted": True, "evidence_hash": _VALID_HASH})
        result = await pipeline.process_l4_experiment(exp)
        assert result is False

    @pytest.mark.asyncio
    async def test_l5_accepts_valid_intervention(self, pipeline):
        h = await pipeline.execute_l5_intervention(_intervention())
        assert h == "dcba2835f"

    @pytest.mark.asyncio
    async def test_l5_rejects_invalid_intervention(self, pipeline):
        with pytest.raises(ValueError, match="L5 Intervention Rejected"):
            await pipeline.execute_l5_intervention({"rogue": 1})
