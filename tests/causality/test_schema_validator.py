# [C5-REAL] Exergy-Maximized
"""
Permanent pytest tests for L0-L6 JSON schema validator.
"""

from __future__ import annotations

import base64
import os
import uuid
from typing import Any, Dict

os.environ.setdefault("CORTEX_TESTING", "1")
os.environ.setdefault(
    "CORTEX_MASTER_KEY",
    base64.b64encode(os.urandom(32)).decode(),
)

import pytest
from cortex.engine.causal.schema_validator import L0L6SchemaValidator

@pytest.fixture
def validator():
    """Provides a initialized L0L6SchemaValidator instance."""
    return L0L6SchemaValidator()

class TestL0L6SchemaValidator:
    """Test suite for verifying strict jsonschema validation across L0-L6 schemas."""

    def test_schema_validator_loads_all_schemas(self, validator):
        """Verify the validator loads all expected schemas from the directory."""
        expected_schemas = {
            "evidence.schema",
            "pattern.schema",
            "model.schema",
            "prediction.schema",
            "experiment.schema",
            "intervention.schema",
        }
        for name in expected_schemas:
            assert name in validator._schemas
            assert "$schema" in validator._schemas[name]

    def test_validate_nonexistent_level(self, validator):
        """Validating a nonexistent schema level must return False."""
        assert validator.validate_payload("nonexistent.schema", {}) is False

    def test_validate_evidence_success(self, validator):
        """Verify a structurally correct L0 evidence payload passes validation."""
        payload = {
            "evidence_id": str(uuid.uuid4()),
            "source_type": "AST_DIFF",
            "payload": "git diff content",
            "timestamp": "2026-06-29T19:18:32Z",
            "cortex_taint_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        }
        assert validator.validate_payload("evidence.schema", payload) is True

    def test_validate_evidence_missing_key(self, validator):
        """Verify evidence payload fails when missing a required key."""
        payload = {
            "evidence_id": str(uuid.uuid4()),
            "source_type": "AST_DIFF",
            "payload": "git diff content",
            "timestamp": "2026-06-29T19:18:32Z",
            # missing cortex_taint_hash
        }
        assert validator.validate_payload("evidence.schema", payload) is False

    def test_validate_evidence_invalid_uuid(self, validator):
        """Verify evidence payload fails when UUID has incorrect format."""
        payload = {
            "evidence_id": "not-a-valid-uuid",
            "source_type": "AST_DIFF",
            "payload": "git diff content",
            "timestamp": "2026-06-29T19:18:32Z",
            "cortex_taint_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        }
        assert validator.validate_payload("evidence.schema", payload) is False

    def test_validate_evidence_invalid_hash(self, validator):
        """Verify evidence payload fails when taint hash format is incorrect."""
        payload = {
            "evidence_id": str(uuid.uuid4()),
            "source_type": "AST_DIFF",
            "payload": "git diff content",
            "timestamp": "2026-06-29T19:18:32Z",
            "cortex_taint_hash": "short-hash",  # must be 64 hex chars
        }
        assert validator.validate_payload("evidence.schema", payload) is False

    def test_validate_pattern_success(self, validator):
        """Verify a structurally correct L1 pattern payload passes validation."""
        payload = {
            "pattern_id": str(uuid.uuid4()),
            "evidence_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "invariant_claim": "Strict WAL journal mode prevents locking contention",
            "shannon_entropy_score": 0.85,
        }
        assert validator.validate_payload("pattern.schema", payload) is True

    def test_validate_pattern_invalid_entropy_range(self, validator):
        """Verify pattern validation fails when shannon entropy is out of [0, 1] bounds."""
        payload = {
            "pattern_id": str(uuid.uuid4()),
            "evidence_ids": [str(uuid.uuid4())],
            "invariant_claim": "Strict WAL journal mode prevents locking contention",
            "shannon_entropy_score": 1.2,  # out of bounds [0, 1]
        }
        assert validator.validate_payload("pattern.schema", payload) is False

    def test_validate_model_success(self, validator):
        """Verify a structurally correct L2 model payload passes validation."""
        payload = {
            "model_id": str(uuid.uuid4()),
            "pattern_ids": [str(uuid.uuid4())],
            "causal_graph": {
                "nodes": ["A", "B", "C"],
                "edges": [{"from": "A", "to": "B", "relation": "causes"}]
            },
            "confidence_level": "HIGH",
        }
        assert validator.validate_payload("model.schema", payload) is True

    def test_validate_model_invalid_enum(self, validator):
        """Verify model validation fails with invalid confidence_level enum."""
        payload = {
            "model_id": str(uuid.uuid4()),
            "pattern_ids": [str(uuid.uuid4())],
            "causal_graph": {},
            "confidence_level": "SUPER_HIGH",  # not in enum
        }
        assert validator.validate_payload("model.schema", payload) is False

    def test_validate_prediction_success(self, validator):
        """Verify a structurally correct L3 prediction payload passes validation."""
        payload = {
            "prediction_id": str(uuid.uuid4()),
            "model_id": str(uuid.uuid4()),
            "falsifiable_condition": "WAL mode results in 0 failures.",
            "experiment_design": {
                "setup_saga": "init WAL database",
                "execution_trigger": "10 concurrent clients",
                "success_criteria": "errors == 0",
            },
            "experiment_result": "PENDING",
        }
        assert validator.validate_payload("prediction.schema", payload) is True

    def test_validate_experiment_success(self, validator):
        """Verify a structurally correct L4 experiment payload passes validation."""
        payload = {
            "experiment_id": str(uuid.uuid4()),
            "prediction_id": str(uuid.uuid4()),
            "execution_context": "SANDBOX_THREAD",
            "outcome": {
                "refuted": False,
                "evidence_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            }
        }
        assert validator.validate_payload("experiment.schema", payload) is True

    def test_validate_intervention_success(self, validator):
        """Verify a structurally correct L5/L6 intervention payload passes validation."""
        payload = {
            "intervention_id": str(uuid.uuid4()),
            "prediction_id": str(uuid.uuid4()),
            "git_sentinel_hash": "a1b2c3d4e5",
            "saga_rollback_plan": "Restore database from journal mode DELETE",
            "l6_reevaluation_status": "PENDING",
        }
        assert validator.validate_payload("intervention.schema", payload) is True
