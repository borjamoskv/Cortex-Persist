# [C5-REAL] Exergy-Maximized
"""CORTEX Health - system-wide monitoring and scoring.

Usage::

    from babylon60.extensions.health import HealthCollector, HealthScorer, Grade

    collector = HealthCollector(db_path="~/.cortex/cortex.db")
    metrics = collector.collect_all()
    score = HealthScorer.score(metrics)
    print(score.grade)  # Grade.SOVEREIGN
"""

from babylon60.extensions.health.collector import (
    CollectorRegistry,
    HealthCollector,
    create_default_registry,
)
from babylon60.extensions.health.health_mixin import HealthMixin
from babylon60.extensions.health.health_protocol import MetricCollectorProtocol
from babylon60.extensions.health.invariants import verify_health_system
from babylon60.extensions.health.models import (
    Grade,
    HealthReport,
    HealthScore,
    HealthSLA,
    HealthSLAViolation,
    HealthThresholds,
    MetricSnapshot,
)
from babylon60.extensions.health.scorer import HealthScorer
from babylon60.extensions.health.trend import TrendDetector

try:
    from babylon60.extensions.health.prometheus import export_prometheus

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
