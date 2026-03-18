"""CORTEX Health — system-wide monitoring and scoring.

Usage::

    from cortex.extensions.health import HealthCollector, HealthScorer, Grade

    collector = HealthCollector(db_path="~/.cortex/cortex.db")
    metrics = collector.collect_all()
    score = HealthScorer.score(metrics)
    print(score.grade)  # Grade.SOVEREIGN
"""

from cortex.extensions.health.collector import (
    CollectorRegistry,
    HealthCollector,
    create_default_registry,
)
from cortex.extensions.health.health_mixin import HealthMixin
from cortex.extensions.health.health_protocol import MetricCollectorProtocol
from cortex.extensions.health.invariants import verify_health_system
from cortex.extensions.health.models import (
    Grade,
    HealthReport,
    HealthScore,
    HealthSLA,
    HealthThresholds,
    MetricSnapshot,
)
from cortex.extensions.health.prometheus import export_prometheus
from cortex.extensions.health.trend import TrendDetector

from .fix_registry import FixRegistry
from .scorer import HealthScorer

__all__ = [
    "CollectorRegistry",
    "Grade",
    "HealthCollector",
    "HealthMixin",
    "HealthReport",
    "HealthScore",
    "HealthSLA",
    "HealthScorer",
    "HealthThresholds",
    "MetricCollectorProtocol",
    "MetricSnapshot",
    "TrendDetector",
    "create_default_registry",
    "export_prometheus",
    "verify_health_system",
]
