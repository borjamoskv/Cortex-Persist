"""
CORTEX — Prometheus Exposition.

Converts a CORTEX HealthReport or HealthScore into the Prometheus
text-based exposition format for ingestion by metrics scrapers.
"""

from __future__ import annotations

from typing import Union, cast

from cortex.extensions.health.models import Grade, HealthReport, HealthScore


def _grade_to_numeric(grade: Grade) -> int:
    """Convert Grade to numeric value (0-5) for graphing."""
    mapping = {
        Grade.FAILED: 0,
        Grade.DEGRADED: 1,
        Grade.ACCEPTABLE: 2,
        Grade.GOOD: 3,
        Grade.EXCELLENT: 4,
        Grade.SOVEREIGN: 5,
    }
    return mapping.get(grade, 0)


def export_prometheus(score_or_report: Union[HealthScore, HealthReport]) -> str:
    """
    Format a CORTEX health payload into Prometheus exposition format.

    Args:
        score_or_report: The calculated HealthScore or HealthReport.

    Returns:
        A multiline string compliant with Prometheus text exposition format.
    """
    if isinstance(score_or_report, HealthReport):
        score = score_or_report.score
    else:
        # Cast to appease type checker if the type intersection is strict
        score = cast(HealthScore, score_or_report)

    lines: list[str] = []

    # ── Overall Score ──────────────────────────────────────────
    lines.append("# HELP cortex_health_score_total Overall CORTEX health score (0-100)")
    lines.append("# TYPE cortex_health_score_total gauge")
    lines.append(f"cortex_health_score_total {score.score:.2f}")
    lines.append("")

    # ── Grade ──────────────────────────────────────────────────
    numeric_grade = _grade_to_numeric(score.grade)
    lines.append("# HELP cortex_health_grade Current grade (0=F, 1=D, 2=C, 3=B, 4=A, 5=S)")
    lines.append("# TYPE cortex_health_grade gauge")
    lines.append(f"cortex_health_grade {numeric_grade}")
    lines.append("")

    # ── Sub-indices ────────────────────────────────────────────
    if score.sub_indices:
        lines.append("# HELP cortex_health_sub_index Composite health sub-indices (0-100)")
        lines.append("# TYPE cortex_health_sub_index gauge")
        for index_name, val in score.sub_indices.items():
            lines.append(f'cortex_health_sub_index{{index="{index_name}"}} {val:.2f}')
        lines.append("")

    # ── Individual Metrics (Value) ─────────────────────────────
    if score.metrics:
        lines.append("# HELP cortex_health_metric_value Individual collector metric values")
        lines.append("# TYPE cortex_health_metric_value gauge")
        for m in score.metrics:
            lines.append(f'cortex_health_metric_value{{collector="{m.name}"}} {m.value:.4f}')
        lines.append("")

        # ── Individual Metrics (Latency) ───────────────────────
        lines.append("# HELP cortex_health_metric_latency_ms Individual collector latency (ms)")
        lines.append("# TYPE cortex_health_metric_latency_ms gauge")
        for m in score.metrics:
            latency = getattr(m, "latency_ms", 0.0)
            lines.append(f'cortex_health_metric_latency_ms{{collector="{m.name}"}} {latency:.2f}')
        lines.append("")

    return "\n".join(lines) + "\n"
