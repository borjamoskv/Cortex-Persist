# [C5-REAL] Exergy-Maximized
"""CORTEX Health - system-wide monitoring and scoring.

Usage::

    from cortex_extensions.health import HealthCollector, HealthScorer, Grade

    collector = HealthCollector(db_path="~/.cortex/cortex.db")
    metrics = collector.collect_all()
    score = HealthScorer.score(metrics)
    print(score.grade)  # Grade.SOVEREIGN
"""

from cortex_extensions.health.collector import (
    CollectorRegistry,
    HealthCollector,
    create_default_registry,
)
from cortex_extensions.health.health_mixin import HealthMixin
from cortex_extensions.health.health_protocol import MetricCollectorProtocol
from cortex_extensions.health.invariants import verify_health_system
from cortex_extensions.health.models import (
    Grade,
    HealthReport,
    HealthScore,
    HealthSLA,
    HealthSLAViolation,
    HealthThresholds,
    MetricSnapshot,
)
from cortex_extensions.health.scorer import HealthScorer
from cortex_extensions.health.trend import TrendDetector

try:
    from cortex_extensions.health.prometheus import export_prometheus

    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    export_prometheus = None  # type: ignore

__all__ = [
    "CollectorRegistry",
    "Grade",
    "HealthCollector",
    "HealthMixin",
    "HealthReport",
    "HealthSLA",
    "HealthSLAViolation",
    "HealthScore",
    "HealthScorer",
    "HealthThresholds",
    "MetricCollectorProtocol",
    "MetricSnapshot",
    "TrendDetector",
    "create_default_registry",
    "export_prometheus",
    "verify_health_system",
]
