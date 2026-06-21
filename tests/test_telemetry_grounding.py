# [C5-REAL] Exergy-Maximized
import json
import pytest
import cortex_rs
from cortex.telemetry.metrics import metrics

def test_rust_telemetry_schema_validation():
    # 1. Valid Raw Metric payload should pass
    raw_payload = {
        "type": "raw",
        "metric": "execution_duration",
        "path": "cortex/api/core.py",
        "duration_ms": 145
    }
    assert cortex_rs.validate_metric_json(json.dumps(raw_payload)) is True

    # 2. Valid Derived Metric payload should pass
    derived_payload = {
        "type": "derived",
        "formula": "exergy_ratio",
        "raw_work_tokens": 100,
        "total_tokens": 150,
        "value": 0.6666
    }
    assert cortex_rs.validate_metric_json(json.dumps(derived_payload)) is True

    # 3. Valid Narrative Claim payload should pass
    narrative_payload = {
        "type": "narrative",
        "label": "system_sovereignty",
        "description": "coherence high, all validation gates passed.",
        "evidence_roots": ["hash_123", "hash_456"]
    }
    assert cortex_rs.validate_metric_json(json.dumps(narrative_payload)) is True

    # 4. Invalid structures must throw value errors
    invalid_payload = {
        "type": "raw",
        "metric": "some_random_heuristic",
        "heuristic_percentage": 98.6
    }
    with pytest.raises(ValueError) as excinfo:
        cortex_rs.validate_metric_json(json.dumps(invalid_payload))
    assert "Invalid epistemic metric schema" in str(excinfo.value)

def test_python_telemetry_integration():
    # Calling increment with invalid typed metric payload metadata should raise ValueError
    invalid_meta = {
        "type": "raw",
        "metric": "serotonin_boost",
        "serotonin_boost": 0.1
    }
    with pytest.raises(ValueError):
        metrics.inc("cortex_ledger_violations_total", value=1, meta=invalid_meta)
