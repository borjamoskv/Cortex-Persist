"""Tests for CORTEX Health — REFACTOR-Ω edition.

Covers all 3 dimensions:
  D1: Sealed Grade enum + validation
  D2: Plugin CollectorRegistry + protocol enforcement
  D3: TrendDetector + self-verification invariants
"""

from __future__ import annotations

import pytest

from cortex.extensions.health.collector import (
    CollectorRegistry,
    DbCollector,
    EntropyCollector,
    FactCountCollector,
    HealthCollector,
    LedgerCollector,
    WalCollector,
    create_default_registry,
)
from cortex.extensions.health.health_mixin import HealthMixin
from cortex.extensions.health.health_protocol import MetricCollectorProtocol
from cortex.extensions.health.invariants import verify_health_system
from cortex.extensions.health.models import (
    Grade,
    HealthReport,
    HealthScore,
    HealthThresholds,
    MetricSnapshot,
)
from cortex.extensions.health.scorer import HealthScorer
from cortex.extensions.health.trend import TrendDetector

# ═══════════════════════════════════════════════════════════════
# D1: SEALED GRADE ENUM
# ═══════════════════════════════════════════════════════════════


class TestGradeEnum:
    def test_all_grades_exist(self):
        assert len(Grade) == 6

    def test_ordering(self):
        assert Grade.SOVEREIGN > Grade.EXCELLENT
        assert Grade.EXCELLENT > Grade.GOOD
        assert Grade.GOOD > Grade.ACCEPTABLE
        assert Grade.ACCEPTABLE > Grade.DEGRADED
        assert Grade.DEGRADED > Grade.FAILED

    def test_from_score_full_range(self):
        assert Grade.from_score(100.0) == Grade.SOVEREIGN
        assert Grade.from_score(95.0) == Grade.SOVEREIGN
        assert Grade.from_score(94.9) == Grade.EXCELLENT
        assert Grade.from_score(85.0) == Grade.EXCELLENT
        assert Grade.from_score(70.0) == Grade.GOOD
        assert Grade.from_score(55.0) == Grade.ACCEPTABLE
        assert Grade.from_score(40.0) == Grade.DEGRADED
        assert Grade.from_score(39.9) == Grade.FAILED
        assert Grade.from_score(0.0) == Grade.FAILED

    def test_from_letter_valid(self):
        assert Grade.from_letter("S") == Grade.SOVEREIGN
        assert Grade.from_letter("F") == Grade.FAILED

    def test_from_letter_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown grade"):
            Grade.from_letter("X")

    def test_emoji_property(self):
        assert Grade.SOVEREIGN.emoji == "👑"
        assert Grade.FAILED.emoji == "🔴"

    def test_str_returns_letter(self):
        assert str(Grade.SOVEREIGN) == "S"
        assert str(Grade.FAILED) == "F"

    def test_repr(self):
        assert "SOVEREIGN" in repr(Grade.SOVEREIGN)

    def test_threshold_property(self):
        assert Grade.SOVEREIGN.threshold == 95.0
        assert Grade.FAILED.threshold == 0.0


# ═══════════════════════════════════════════════════════════════
# D1: MODELS VALIDATION
# ═══════════════════════════════════════════════════════════════


class TestMetricSnapshot:
    def test_frozen(self):
        m = MetricSnapshot(name="db", value=0.5)
        with pytest.raises(AttributeError):
            m.value = 0.9  # type: ignore[misc]

    def test_value_clamped_high(self):
        m = MetricSnapshot(name="db", value=1.5)
        assert m.value == 1.0

    def test_value_clamped_low(self):
        m = MetricSnapshot(name="db", value=-0.5)
        assert m.value == 0.0

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            MetricSnapshot(name="", value=0.5)

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError):
            MetricSnapshot(name="db", value=0.5, weight=-1.0)

    def test_remediation_field(self):
        hs = MetricSnapshot(name="db", value=1.0, remediation="Fix db")
        assert hs.remediation == "Fix db"
        assert hs.latency_ms == 0.0


class TestHealthScore:
    def test_grade_must_be_enum(self):
        with pytest.raises(TypeError, match="Grade enum"):
            HealthScore(score=50.0, grade="A")  # type: ignore[arg-type]

    def test_score_clamped(self):
        hs = HealthScore(score=150.0, grade=Grade.SOVEREIGN)
        assert hs.score == 100.0

    def test_healthy_property(self):
        assert (
            HealthScore(
                score=50.0,
                grade=Grade.ACCEPTABLE,
            ).healthy
            is True
        )
        assert (
            HealthScore(
                score=30.0,
                grade=Grade.FAILED,
            ).healthy
            is False
        )

    def test_to_dict_letter_not_enum(self):
        hs = HealthScore(score=85.0, grade=Grade.EXCELLENT)
        d = hs.to_dict()
        assert d["grade"] == "A"
        assert isinstance(d["grade"], str)


class TestHealthReport:
    def test_is_critical_with_warnings(self):
        report = HealthReport(
            score=HealthScore(score=80.0, grade=Grade.GOOD),
            warnings=["Something bad"],
        )
        assert report.is_critical is True

    def test_is_critical_grade_degraded(self):
        report = HealthReport(
            score=HealthScore(
                score=35.0,
                grade=Grade.FAILED,
            ),
        )
        assert report.is_critical is True

    def test_not_critical(self):
        report = HealthReport(
            score=HealthScore(score=90.0, grade=Grade.EXCELLENT),
        )
        assert report.is_critical is False

    def test_trend_field(self):
        report = HealthReport(
            score=HealthScore(score=90.0, grade=Grade.EXCELLENT),
            trend="improving",
        )
        d = report.to_dict()
        assert d["trend"] == "improving"


class TestHealthThresholds:
    def test_frozen(self):
        t = HealthThresholds()
        with pytest.raises(AttributeError):
            t.critical = 0.1  # type: ignore[misc]

    def test_defaults(self):
        t = HealthThresholds()
        assert t.critical == 0.3
        assert t.degraded == 0.5
        assert t.improve == 0.8

    def test_custom(self):
        t = HealthThresholds(critical=0.1, db_warn_mb=200)
        assert t.critical == 0.1
        assert t.db_warn_mb == 200


# ═══════════════════════════════════════════════════════════════
# D2: PLUGIN COLLECTOR REGISTRY
# ═══════════════════════════════════════════════════════════════


class TestCollectorRegistry:
    def test_register_valid(self):
        reg = CollectorRegistry()
        reg.register(DbCollector())
        assert "db" in reg

    def test_register_invalid_raises(self):
        reg = CollectorRegistry()
        with pytest.raises(TypeError, match="MetricCollectorProtocol"):
            reg.register("not a collector")

    def test_register_duplicate_raises(self):
        reg = CollectorRegistry()
        reg.register(DbCollector())
        with pytest.raises(ValueError, match="already registered"):
            reg.register(DbCollector())

    def test_unregister(self):
        reg = CollectorRegistry()
        reg.register(DbCollector())
        reg.unregister("db")
        assert "db" not in reg

    def test_collect_all(self):
        reg = create_default_registry()
        results = reg.collect_all("/tmp/nonexistent.db")
        assert len(results) == 6
        for r in results:
            assert isinstance(r, MetricSnapshot)
            assert 0.0 <= r.value <= 1.0

    def test_default_registry_has_5_collectors(self):
        reg = create_default_registry()
        assert len(reg) == 6

    def test_registry_truthiness(self):
        reg = CollectorRegistry()
        assert bool(reg) is True
        reg.register(DbCollector())
        assert bool(reg) is True

    def test_list_collectors(self):
        reg = create_default_registry()
        names = reg.list_collectors()
        expected = {"db", "ledger", "entropy", "facts", "wal", "sysload"}
        assert set(names) == expected


class TestProtocolEnforcement:
    def test_builtin_collectors_conform(self):
        from cortex.extensions.health.collector import SystemLoadCollector

        for cls in [
            DbCollector,
            LedgerCollector,
            EntropyCollector,
            FactCountCollector,
            WalCollector,
            SystemLoadCollector,
        ]:
            instance = cls()
            assert isinstance(instance, MetricCollectorProtocol)
            assert isinstance(instance.name, str)
            assert isinstance(instance.weight, float)


class TestHealthCollectorFacade:
    def test_backward_compatible(self):
        hc = HealthCollector(db_path="/tmp/nonexistent.db")
        metrics = hc.collect_all()
        assert len(metrics) == 6

    def test_registry_accessible(self):
        hc = HealthCollector(db_path="/tmp/nonexistent.db")
        assert len(hc.registry) == 6


# ═══════════════════════════════════════════════════════════════
# D2: SCORER
# ═══════════════════════════════════════════════════════════════


class TestHealthScorer:
    def test_empty_metrics(self):
        hs = HealthScorer.score([])
        assert hs.grade == Grade.FAILED

    def test_perfect_score(self):
        metrics = [
            MetricSnapshot(name="db", value=1.0, weight=1.5),
            MetricSnapshot(name="ledger", value=1.0, weight=1.2),
        ]
        hs = HealthScorer.score(metrics)
        assert hs.score == 100.0
        assert hs.grade == Grade.SOVEREIGN

    def test_classify_returns_grade_enum(self):
        g = HealthScorer.classify(95.0)
        assert isinstance(g, Grade)
        assert g == Grade.SOVEREIGN

    def test_weight_overrides(self):
        metrics = [
            MetricSnapshot(name="db", value=1.0, weight=1.0),
            MetricSnapshot(name="ledger", value=0.0, weight=1.0),
        ]
        hs = HealthScorer.score(
            metrics,
            weights={"db": 100.0, "ledger": 0.001},
        )
        assert hs.score > 95.0

    def test_sub_indices_calculation(self):
        metrics = [
            MetricSnapshot(name="db", value=0.8, weight=1.0),
            MetricSnapshot(name="facts", value=0.4, weight=1.0),
            MetricSnapshot(name="ledger", value=1.0, weight=1.0),
        ]
        hs = HealthScorer.score(metrics)
        # Storage = (0.8 + 0.4) / 2 = 0.6 = 60.0
        # Integrity = 1.0 = 100.0
        assert "storage" in hs.sub_indices
        assert hs.sub_indices["storage"] == 60.0
        assert "integrity" in hs.sub_indices
        assert hs.sub_indices["integrity"] == 100.0
        assert "performance" not in hs.sub_indices

    def test_summarize_uses_emoji(self):
        hs = HealthScore(score=97.0, grade=Grade.SOVEREIGN)
        s = HealthScorer.summarize(hs)
        assert "👑" in s


# ═══════════════════════════════════════════════════════════════
# D3: TREND DETECTOR
# ═══════════════════════════════════════════════════════════════


class TestTrendDetector:
    def test_initial_stable(self):
        td = TrendDetector()
        assert td.detect_drift() == "stable"
        assert td.slope() == 0.0

    def test_improving(self):
        td = TrendDetector()
        for i in range(5):
            td.push(50.0 + i * 5)
        assert td.detect_drift() == "improving"
        assert td.slope() > 0

    def test_degrading(self):
        td = TrendDetector()
        for i in range(5):
            td.push(90.0 - i * 5)
        assert td.detect_drift() == "degrading"
        assert td.slope() < 0

    def test_stable_flat(self):
        td = TrendDetector()
        for _ in range(5):
            td.push(75.0)
        assert td.detect_drift() == "stable"
        assert abs(td.slope()) < 0.01

    def test_ring_buffer_size(self):
        td = TrendDetector(window_size=3)
        for i in range(10):
            td.push(float(i))
        assert td.sample_count == 3

    def test_repr(self):
        td = TrendDetector()
        td.push(80.0)
        r = repr(td)
        assert "TrendDetector" in r
        assert "drift=" in r


# ═══════════════════════════════════════════════════════════════
# D3: INVARIANT SELF-CHECK
# ═══════════════════════════════════════════════════════════════


class TestInvariants:
    def test_default_system_sound(self):
        """The built-in health system must pass ALL invariants."""
        violations = verify_health_system()
        assert violations == [], f"Invariant violations: {violations}"

    def test_custom_registry_fails_if_empty(self):
        reg = CollectorRegistry()
        violations = verify_health_system(registry=reg)
        # Empty registry should have violations
        assert len(violations) > 0


# ═══════════════════════════════════════════════════════════════
# MIXIN
# ═══════════════════════════════════════════════════════════════


class TestHealthMixin:
    @pytest.mark.asyncio
    async def test_health_check_grade_is_string(self):
        class E(HealthMixin):
            _db_path = "/tmp/nonexistent.db"

        result = await E().health_check()
        assert isinstance(result["grade"], str)

    @pytest.mark.asyncio
    async def test_health_score_returns_grade_enum(self):
        class E(HealthMixin):
            _db_path = "/tmp/nonexistent.db"

        hs = await E().health_score()
        assert isinstance(hs.grade, Grade)

    @pytest.mark.asyncio
    async def test_health_report_has_trend(self):
        class E(HealthMixin):
            _db_path = "/tmp/nonexistent.db"

        rep = await E().health_report()
        assert rep.trend in {"improving", "stable", "degrading"}

    @pytest.mark.asyncio
    async def test_collector_cached(self):
        class E(HealthMixin):
            _db_path = "/tmp/nonexistent.db"

        e = E()
        await e.health_check()
        c1 = e._health_collector
        await e.health_check()
        c2 = e._health_collector
        assert c1 is c2
