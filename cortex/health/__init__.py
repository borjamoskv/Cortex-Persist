"""CORTEX Health — system-wide monitoring and scoring.

Usage::

    from cortex.health import HealthCollector, HealthScorer, Grade

    collector = HealthCollector(db_path="~/.cortex/cortex.db")
    metrics = collector.collect_all()
    score = HealthScorer.score(metrics)
    print(score.grade)  # Grade.SOVEREIGN
"""

from cortex.health.collector import (
    CollectorRegistry,
    HealthCollector,
    create_default_registry,
)
from cortex.health.health_mixin import HealthMixin
from cortex.health.health_protocol import MetricCollectorProtocol
from cortex.health.invariants import verify_health_system
from cortex.health.models import (
    Grade,
    HealthReport,
    HealthScore,
    HealthThresholds,
    MetricSnapshot,
)
from cortex.health.prometheus import export_prometheus
from cortex.health.scorer import HealthScorer
from cortex.health.trend import TrendDetector

__all__ = [
    "CollectorRegistry",
    "Grade",
    "HealthCollector",
    "HealthMixin",
    "HealthReport",
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
