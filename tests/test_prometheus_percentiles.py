# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""Tests for Prometheus metrics percentile rendering."""

from __future__ import annotations

from cortex.telemetry.metrics import MetricsRegistry


class TestPrometheusPercentiles:
    """Test the improved percentile rendering in to_prometheus()."""

    def test_histogram_percentiles_rendered(self):
        """Histogram should render p50, p95, p99 quantile lines."""
        reg = MetricsRegistry()
        # Add 100 observations: 0.01, 0.02, ..., 1.00
        for i in range(1, 101):
            reg.observe("cortex_test_duration_seconds", i * 0.01)

        output = reg.to_prometheus()

        assert 'quantile="0.5"' in output
        assert 'quantile="0.95"' in output
        assert 'quantile="0.99"' in output
        assert "cortex_test_duration_seconds_count 100" in output
        assert "cortex_test_duration_seconds_sum" in output

    def test_histogram_single_observation(self):
        """Single observation should still produce valid output."""
        reg = MetricsRegistry()
        reg.observe("cortex_latency", 0.042)

        output = reg.to_prometheus()

        # All quantiles should equal the single value
        assert "0.042000" in output
        assert "cortex_latency_count 1" in output

    def test_histogram_with_labels(self):
        """Labeled histograms should include labels in count/sum keys."""
        reg = MetricsRegistry()
        labels = {"method": "GET", "status": "200"}
        reg.observe("cortex_http_duration", 0.1, labels)
        reg.observe("cortex_http_duration", 0.2, labels)

        output = reg.to_prometheus()

        # Count/sum include label keys
        assert "_count 2" in output
        assert 'quantile="0.5"' in output

    def test_empty_histogram_no_output(self):
        """Empty registry should produce minimal output."""
        reg = MetricsRegistry()
        output = reg.to_prometheus()
        assert output.strip() == ""

    def test_percentile_accuracy(self):
        """p50 should be close to median, p99 near maximum."""
        reg = MetricsRegistry()
        # 0.001 .. 1.000
        for i in range(1, 1001):
            reg.observe("latency", i * 0.001)

        output = reg.to_prometheus()
        lines = output.strip().split("\n")

        quantile_lines = [line for line in lines if "quantile=" in line]
        assert len(quantile_lines) == 3

        # p50 ~ 0.5, p95 ~ 0.95, p99 ~ 0.99
        for line in quantile_lines:
            parts = line.split()
            value = float(parts[1])
            if "0.5" in parts[0]:
                assert 0.45 <= value <= 0.55, f"p50 out of range: {value}"
            elif "0.95" in parts[0]:
                assert 0.90 <= value <= 1.0, f"p95 out of range: {value}"
            elif "0.99" in parts[0]:
                assert 0.95 <= value <= 1.01, f"p99 out of range: {value}"

    def test_counter_and_gauge_unaffected(self):
        """Counter and gauge rendering should remain unchanged."""
        reg = MetricsRegistry()
        reg.inc("cortex_requests_total", value=42)
        reg.set_gauge("cortex_memory_mb", 128.5)

        output = reg.to_prometheus()

        assert "cortex_requests_total 42" in output
        assert "cortex_memory_mb 128.50" in output
        assert "# TYPE cortex_requests_total counter" in output
        assert "# TYPE cortex_memory_mb gauge" in output
