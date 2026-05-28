"""Tests for the Prometheus exposition module."""

from cortex.extensions.health.models import Grade, HealthScore, MetricSnapshot
from cortex.extensions.health.prometheus import export_prometheus


def test_export_prometheus_formats_correctly() -> None:
    score = HealthScore(
        score=82.5,
        grade=Grade.EXCELLENT,
        metrics=[
            MetricSnapshot(name="db", value=0.9, weight=1.0, latency_ms=15.5),
        ],
        sub_indices={"storage": 90.0},
    )

    output = export_prometheus(score)

    assert "cortex_health_score_total 82.50" in output
    assert "cortex_health_grade 4" in output  # EXCELLENT
    assert 'cortex_health_sub_index{index="storage"} 90.00' in output
    assert 'cortex_health_metric_value{collector="db"} 0.9000' in output
    assert 'cortex_health_metric_latency_ms{collector="db"} 15.50' in output
