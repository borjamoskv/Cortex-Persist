# [C5-REAL] Exergy-Maximized
"""CORTEX Health - system-wide monitoring and scoring.

Usage::

    from legacy_research.extensions.health import HealthCollector, HealthScorer, Grade

    collector = HealthCollector(db_path="~/.cortex/cortex.db")
    metrics = collector.collect_all()
    score = HealthScorer.score(metrics)
    print(score.grade)  # Grade.SOVEREIGN
"""

from legacy_research.extensions.health.collector import (
    CollectorRegistry,
    HealthCollector,
    create_default_registry,
)
from legacy_research.extensions.health.health_mixin import HealthMixin
from legacy_research.extensions.health.health_protocol import MetricCollectorProtocol
from legacy_research.extensions.health.invariants import verify_health_system
from legacy_research.extensions.health.models import (
    Grade,
    HealthReport,
    HealthScore,
    HealthSLA,
    HealthSLAViolation,
    HealthThresholds,
    MetricSnapshot,
)
from legacy_research.extensions.health.scorer import HealthScorer
from legacy_research.extensions.health.trend import TrendDetector

try:
    from legacy_research.extensions.health.prometheus import export_prometheus

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
