# [C5-REAL] Exergy-Maximized
import pytest
import json
from cortex_rs import validate_metric_json
from cortex.telemetry.metrics import MetricsRegistry, validate_typed_metric


class TestRustTelemetrySchemaValidation:
    """Verify that the Rust-side schema enforces type boundaries."""

    def test_valid_raw_metric(self):
        payload = json.dumps({
            "kind": "Raw",
            "name": "cpu.utilization",
            "value": 73.2,
            "unit": "percent",
            "source": "prometheus",
            "timestamp_epoch_ms": 1717027200000,
        })
        result = validate_metric_json(payload)
        assert result == "Raw"

    def test_valid_derived_metric(self):
        payload = json.dumps({
            "kind": "Derived",
            "name": "latency.p95.delta.24h",
            "value": -12.5,
            "unit": "ms",
            "derivation": "p95(now) - p95(now - 24h)",
            "source_metrics": ["latency.p95"],
            "timestamp_epoch_ms": 1717027200000,
        })
        result = validate_metric_json(payload)
        assert result == "Derived"

    def test_valid_narrative_claim(self):
        payload = json.dumps({
            "kind": "Narrative",
            "claim": "System responsiveness improved after cache warmup",
            "context": "manual observation during load test",
            "confidence": "medium",
        })
        result = validate_metric_json(payload)
        assert result == "Narrative"

    def test_rejects_untyped_payload(self):
        payload = json.dumps({
            "exergy_ratio": 0.42,
            "vibe": "high",
        })
        with pytest.raises(ValueError, match="Telemetry validation failed"):
            validate_metric_json(payload)

    def test_rejects_missing_required_fields(self):
        payload = json.dumps({
            "kind": "Raw",
            "name": "cpu.utilization",
            # missing: value, unit, source, timestamp_epoch_ms
        })
        with pytest.raises(ValueError, match="Telemetry validation failed"):
            validate_metric_json(payload)


class TestPythonTelemetryIntegration:
    """Verify that MetricsRegistry enforces schemas end-to-end."""

    def test_inc_with_valid_payload(self):
        registry = MetricsRegistry()
        payload = {
            "kind": "Raw",
            "name": "request.count",
            "value": 1.0,
            "unit": "count",
            "source": "nginx_access_log",
            "timestamp_epoch_ms": 1717027200000,
        }
        registry.inc("request.count", 1.0, payload=payload)
        assert registry.get("request.count") == 1.0
        meta = registry.get_metadata("request.count")
        assert meta["epistemic_kind"] == "Raw"

    def test_inc_without_payload_still_works(self):
        registry = MetricsRegistry()
        registry.inc("simple.counter", 5.0)
        assert registry.get("simple.counter") == 5.0
        assert registry.get_metadata("simple.counter") is None

    def test_inc_with_invalid_payload_raises(self):
        registry = MetricsRegistry()
        bad_payload = {"serotonin_boost": 1.0}
        with pytest.raises(ValueError):
            registry.inc("fake.metric", 1.0, payload=bad_payload)
