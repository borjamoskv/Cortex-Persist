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
    HealthSLAViolation,
    MetricSnapshot,
)

from .fix_registry import FixRegistry
from .scorer import HealthScorer
from .trend import TrendDetector

__all__ = [
    "Grade",
    "HealthReport",
    "HealthScore",
    "HealthSLA",
    "HealthSLAViolation",
    "MetricSnapshot",
    "HealthScorer",
    "FixRegistry",
    "TrendDetector",
    "verify_health_system",
]
