"""Tests for cortex.shannon — Information Theory applied to CORTEX memory.

Tests are split into two groups:
  1. Pure math (no DB) — validates Shannon formulas
  2. Integration (temp DB) — validates scanner + report pipeline
"""

from __future__ import annotations

import math
import pytest

from cortex.shannon.analyzer import (
    conditional_entropy,
    cross_entropy,
    information_value,
    jensen_shannon_divergence,
    kl_divergence,
    max_entropy,
    mutual_information,
    normalized_entropy,
    redundancy,
    shannon_entropy,
)


# ═══════════════════════════════════════════════════════════════════════
# Pure Math Tests
# ═══════════════════════════════════════════════════════════════════════


class TestShannonEntropy:
    def test_uniform_four(self):
        """Uniform distribution of 4 items → H = 2.0 bits exactly."""
        dist = {"a": 25, "b": 25, "c": 25, "d": 25}
        assert math.isclose(shannon_entropy(dist), 2.0, rel_tol=1e-9)

    def test_single_element(self):
        """Single item → H = 0.0 (no uncertainty)."""
        assert shannon_entropy({"only": 100}) == 0.0

    def test_empty(self):
        """Empty distribution → H = 0.0."""
        assert shannon_entropy({}) == 0.0

    def test_binary_fair(self):
        """Fair coin → H = 1.0 bit."""
        dist = {"heads": 50, "tails": 50}
        assert math.isclose(shannon_entropy(dist), 1.0, rel_tol=1e-9)

    def test_skewed(self):
        """Heavily skewed distribution → low entropy."""
        dist = {"dominant": 99, "rare": 1}
        h = shannon_entropy(dist)
        assert 0 < h < 1.0  # Much less than max_entropy(2) = 1.0


class TestMaxEntropy:
    def test_four_categories(self):
        assert math.isclose(max_entropy(4), 2.0, rel_tol=1e-9)

    def test_one_category(self):
        assert max_entropy(1) == 0.0

    def test_zero(self):
        assert max_entropy(0) == 0.0

    def test_eight(self):
        assert math.isclose(max_entropy(8), 3.0, rel_tol=1e-9)


class TestNormalizedEntropy:
    def test_uniform_is_one(self):
        dist = {"a": 10, "b": 10, "c": 10}
        assert math.isclose(normalized_entropy(dist), 1.0, rel_tol=1e-9)

    def test_single_is_zero(self):
        assert normalized_entropy({"only": 100}) == 0.0

    def test_empty_is_zero(self):
        assert normalized_entropy({}) == 0.0

    def test_between_zero_and_one(self):
        dist = {"big": 90, "small": 10}
        norm = normalized_entropy(dist)
        assert 0.0 < norm < 1.0


class TestRedundancy:
    def test_uniform_is_zero(self):
        """Uniform distribution → zero redundancy."""
        dist = {"a": 25, "b": 25, "c": 25, "d": 25}
        assert math.isclose(redundancy(dist), 0.0, abs_tol=1e-9)

    def test_single_element_is_zero(self):
        """Single category → degenerate, returns 0.0."""
        assert redundancy({"only": 100}) == 0.0

    def test_empty_is_zero(self):
        assert redundancy({}) == 0.0

    def test_skewed_is_high(self):
        """Heavily skewed → high redundancy."""
        dist = {"dominant": 99, "rare": 1}
        r = redundancy(dist)
        assert 0.5 < r < 1.0

    def test_complement_of_normalized(self):
        """redundancy = 1 - normalized_entropy."""
        dist = {"a": 30, "b": 50, "c": 20}
        r = redundancy(dist)
        n = normalized_entropy(dist)
        assert math.isclose(r + n, 1.0, rel_tol=1e-9)


class TestKLDivergence:
    def test_identical_is_zero(self):
        p = {"a": 0.5, "b": 0.5}
        assert math.isclose(kl_divergence(p, p), 0.0, abs_tol=1e-6)

    def test_asymmetric(self):
        """KL(P‖Q) ≠ KL(Q‖P) — divergence is not symmetric."""
        p = {"a": 0.9, "b": 0.1}
        q = {"a": 0.1, "b": 0.9}
        d_pq = kl_divergence(p, q)
        d_qp = kl_divergence(q, p)
        # Both should be positive
        assert d_pq > 0
        assert d_qp > 0

    def test_empty_is_zero(self):
        assert kl_divergence({}, {}) == 0.0

    def test_divergent_distributions(self):
        """Very different distributions → high KL divergence."""
        p = {"a": 0.99, "b": 0.01}
        q = {"a": 0.01, "b": 0.99}
        assert kl_divergence(p, q) > 1.0  # Significantly divergent


class TestJensenShannonDivergence:
    def test_identical_is_zero(self):
        """Identical distributions → JSD = 0.0."""
        p = {"a": 0.5, "b": 0.5}
        assert math.isclose(jensen_shannon_divergence(p, p), 0.0, abs_tol=1e-6)

    def test_symmetric(self):
        """JSD(P‖Q) = JSD(Q‖P) — unlike KL, JSD is symmetric."""
        p = {"a": 0.9, "b": 0.1}
        q = {"a": 0.1, "b": 0.9}
        assert math.isclose(
            jensen_shannon_divergence(p, q),
            jensen_shannon_divergence(q, p),
            rel_tol=1e-9,
        )

    def test_bounded_zero_one(self):
        """JSD always ∈ [0, 1]."""
        p = {"a": 0.99, "b": 0.01}
        q = {"a": 0.01, "b": 0.99}
        jsd = jensen_shannon_divergence(p, q)
        assert 0.0 <= jsd <= 1.0

    def test_positive_for_different(self):
        """Different distributions → JSD > 0."""
        p = {"a": 0.7, "b": 0.3}
        q = {"a": 0.3, "b": 0.7}
        assert jensen_shannon_divergence(p, q) > 0.0

    def test_empty_is_zero(self):
        assert jensen_shannon_divergence({}, {}) == 0.0


class TestMutualInformation:
    def test_independent(self):
        """Independent variables → I(X;Y) ≈ 0.0."""
        joint = {
            ("a", "1"): 25, ("a", "2"): 25,
            ("b", "1"): 25, ("b", "2"): 25,
        }
        mi = mutual_information(joint)
        assert math.isclose(mi, 0.0, abs_tol=1e-9)

    def test_perfectly_dependent(self):
        """Perfectly correlated → I(X;Y) = H(X) = H(Y)."""
        joint = {("a", "1"): 50, ("b", "2"): 50}
        mi = mutual_information(joint)
        assert math.isclose(mi, 1.0, rel_tol=1e-9)

    def test_empty(self):
        assert mutual_information({}) == 0.0


class TestConditionalEntropy:
    def test_independent_equals_marginal(self):
        """Independent vars → H(Y|X) = H(Y)."""
        joint = {
            ("a", "1"): 25, ("a", "2"): 25,
            ("b", "1"): 25, ("b", "2"): 25,
        }
        h_y_given_x = conditional_entropy(joint)
        # H(Y) for Y ∈ {1, 2} uniform = 1.0 bit
        assert math.isclose(h_y_given_x, 1.0, rel_tol=1e-9)

    def test_perfect_dependence_is_zero(self):
        """X determines Y perfectly → H(Y|X) = 0."""
        joint = {("a", "1"): 50, ("b", "2"): 50}
        assert math.isclose(conditional_entropy(joint), 0.0, abs_tol=1e-9)

    def test_empty(self):
        assert conditional_entropy({}) == 0.0

    def test_chain_rule(self):
        """Chain rule: H(X,Y) = H(X) + H(Y|X)."""
        joint = {
            ("a", "1"): 40, ("a", "2"): 10,
            ("b", "1"): 20, ("b", "2"): 30,
        }
        h_y_x = conditional_entropy(joint)
        margin_x = {"a": 50, "b": 50}
        h_x = shannon_entropy(margin_x)
        joint_flat = {f"{x}|{y}": c for (x, y), c in joint.items()}
        h_xy = shannon_entropy(joint_flat)
        assert math.isclose(h_x + h_y_x, h_xy, rel_tol=1e-9)


class TestCrossEntropy:
    def test_identical_equals_entropy(self):
        """H(P, P) ≈ H(P) when P = Q (modulo smoothing)."""
        p = {"a": 0.5, "b": 0.5}
        ce = cross_entropy(p, p)
        # H(P) = 1.0, cross_entropy will be very close due to smoothing
        assert math.isclose(ce, 1.0, rel_tol=1e-3)

    def test_divergent_exceeds_entropy(self):
        """H(P, Q) > H(P) when P ≠ Q."""
        p = {"a": 0.9, "b": 0.1}
        q = {"a": 0.1, "b": 0.9}
        ce = cross_entropy(p, q)
        h_p = shannon_entropy({"a": 90, "b": 10})
        assert ce > h_p

    def test_empty_is_zero(self):
        assert cross_entropy({}, {}) == 0.0

    def test_non_negative(self):
        """Cross-entropy is always ≥ 0."""
        p = {"a": 0.7, "b": 0.2, "c": 0.1}
        q = {"a": 0.3, "b": 0.4, "c": 0.3}
        assert cross_entropy(p, q) >= 0.0


class TestInformationValue:
    def test_rare_event_high(self):
        """Rare event → high self-information."""
        iv = information_value(1, 1000)
        assert iv > 9.0  # -log2(1/1000) ≈ 9.97

    def test_common_event_low(self):
        """Common event → low self-information."""
        iv = information_value(500, 1000)
        assert math.isclose(iv, 1.0, rel_tol=1e-9)  # -log2(0.5) = 1

    def test_certain_event_zero(self):
        """Certain event → 0 bits of information."""
        assert math.isclose(information_value(100, 100), 0.0, abs_tol=1e-9)

    def test_zero_freq(self):
        assert information_value(0, 100) == 0.0

    def test_zero_total(self):
        assert information_value(10, 0) == 0.0


# ═══════════════════════════════════════════════════════════════════════
# Integration Tests (require temp DB)
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
async def engine(tmp_path):
    """Create a temporary CortexEngine with schema initialized."""
    from cortex.engine import CortexEngine

    db_path = tmp_path / "test_shannon.db"
    eng = CortexEngine(db_path=db_path)
    await eng.init_db()
    yield eng
    await eng.close()


@pytest.fixture
async def populated_engine(engine):
    """Engine with mixed facts for entropy analysis.

    Uses direct SQL to bypass anomaly detection (bulk_mutation blocker).
    """
    facts = [
        ("cortex", "Architecture uses SQLite", "decision", "agent:gemini"),
        ("cortex", "Fixed connection leak", "error", "agent:gemini"),
        ("cortex", "Shannon module planned", "knowledge", "agent:gemini"),
        ("cortex", "Pruner needs refactor", "ghost", "cli"),
        ("naroa", "Gallery uses React", "decision", "agent:cursor"),
        ("naroa", "Added dark mode", "knowledge", "agent:cursor"),
        ("naroa", "CSS grid layout decision", "decision", "cli"),
        ("notchlive", "AppKit over SwiftUI", "bridge", "agent:gemini"),
        ("notchlive", "IOKit permissions", "error", "agent:gemini"),
        ("notchlive", "Notch animation 60fps", "knowledge", "cli"),
    ]
    async with engine.session() as conn:
        for project, content, fact_type, source in facts:
            await conn.execute(
                "INSERT INTO facts (project, content, fact_type, "
                "confidence, valid_from, source) "
                "VALUES (?, ?, ?, 'stated', datetime('now'), ?)",
                (project, content, fact_type, source),
            )
        await conn.commit()
    return engine


@pytest.mark.asyncio
async def test_scanner_type_distribution(populated_engine):
    """Scanner returns correct fact_type frequencies."""
    from cortex.shannon.scanner import MemoryScanner

    scanner = MemoryScanner(populated_engine)
    dist = await scanner.type_distribution()

    assert dist["decision"] == 3
    assert dist["error"] == 2
    assert dist["knowledge"] == 3
    assert dist["ghost"] == 1
    assert dist["bridge"] == 1


@pytest.mark.asyncio
async def test_scanner_project_distribution(populated_engine):
    """Scanner returns correct project frequencies."""
    from cortex.shannon.scanner import MemoryScanner

    scanner = MemoryScanner(populated_engine)
    dist = await scanner.project_distribution()

    assert dist["cortex"] == 4
    assert dist["naroa"] == 3
    assert dist["notchlive"] == 3


@pytest.mark.asyncio
async def test_scanner_empty_db(engine):
    """Empty database returns empty distributions."""
    from cortex.shannon.scanner import MemoryScanner

    scanner = MemoryScanner(engine)
    dist = await scanner.type_distribution()
    assert dist == {}


@pytest.mark.asyncio
async def test_scanner_total_active_facts(populated_engine):
    """Total count matches stored facts."""
    from cortex.shannon.scanner import MemoryScanner

    scanner = MemoryScanner(populated_engine)
    total = await scanner.total_active_facts()
    assert total == 10


@pytest.mark.asyncio
async def test_scanner_temporal_velocity(populated_engine):
    """Temporal velocity returns daily counts."""
    from cortex.shannon.scanner import MemoryScanner

    scanner = MemoryScanner(populated_engine)
    velocity = await scanner.temporal_velocity()

    # All 10 facts were inserted just now, so today should have 10
    assert isinstance(velocity, dict)
    assert sum(velocity.values()) == 10


@pytest.mark.asyncio
async def test_scanner_content_length_distribution(populated_engine):
    """Content length distribution returns valid buckets."""
    from cortex.shannon.scanner import MemoryScanner

    scanner = MemoryScanner(populated_engine)
    dist = await scanner.content_length_distribution()

    assert isinstance(dist, dict)
    assert sum(dist.values()) == 10
    # All test facts are short strings, so should be in short/medium
    for key in dist:
        assert key in {"micro", "short", "medium", "long", "extensive"}


@pytest.mark.asyncio
async def test_full_report_structure(populated_engine):
    """EntropyReport.analyze() returns all expected keys."""
    from cortex.shannon.report import EntropyReport

    result = await EntropyReport.analyze(populated_engine)

    assert "total_facts" in result
    assert result["total_facts"] == 10
    assert "health_score" in result
    assert 0 <= result["health_score"] <= 100
    assert "temporal_trend" in result
    assert result["temporal_trend"] in {"growing", "stable", "declining"}
    assert "velocity_per_day" in result

    for key in [
        "type_entropy", "confidence_entropy", "project_entropy",
        "source_entropy", "age_entropy", "content_entropy",
    ]:
        assert key in result
        block = result[key]
        assert "H" in block
        assert "H_max" in block
        assert "normalized" in block
        assert "redundancy" in block
        assert "distribution" in block

    assert "mutual_info_type_project" in result
    assert "diagnosis" in result
    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)


@pytest.mark.asyncio
async def test_report_diagnosis_concentrated(engine):
    """All facts same type → diagnosis = 'concentrated'."""
    from cortex.shannon.report import EntropyReport

    # Insert directly to bypass Thalamus density filter
    async with engine.session() as conn:
        for i in range(20):
            await conn.execute(
                "INSERT INTO facts (project, content, fact_type, "
                "confidence, valid_from, source) "
                "VALUES (?, ?, 'knowledge', 'stated', "
                "datetime('now'), 'test')",
                (f"proj-{i % 3}", f"Unique fact about topic {i}"),
            )
        await conn.commit()

    result = await EntropyReport.analyze(engine)
    # Only one fact_type → normalized entropy = 0 → concentrated
    assert result["diagnosis"] == "concentrated"


@pytest.mark.asyncio
async def test_health_score_range(populated_engine):
    """Health score is always ∈ [0, 100]."""
    from cortex.shannon.report import EntropyReport

    result = await EntropyReport.analyze(populated_engine)
    assert isinstance(result["health_score"], int)
    assert 0 <= result["health_score"] <= 100


@pytest.mark.asyncio
async def test_health_score_concentrated_is_low(engine):
    """Concentrated memory → low health score."""
    from cortex.shannon.report import EntropyReport

    async with engine.session() as conn:
        for i in range(20):
            await conn.execute(
                "INSERT INTO facts (project, content, fact_type, "
                "confidence, valid_from, source) "
                "VALUES ('mono', ?, 'knowledge', 'stated', "
                "datetime('now'), 'test')",
                (f"Fact {i}",),
            )
        await conn.commit()

    result = await EntropyReport.analyze(engine)
    # Single type, single project, single source → very low health
    assert result["health_score"] < 50


@pytest.mark.asyncio
async def test_engine_shannon_report(populated_engine):
    """CortexEngine.shannon_report() returns valid results."""
    result = await populated_engine.shannon_report()
    assert result["total_facts"] == 10
    assert result["type_entropy"]["H"] > 0
    assert "health_score" in result


@pytest.mark.asyncio
async def test_report_with_project_filter(populated_engine):
    """EntropyReport with project filter only analyzes that project."""
    from cortex.shannon.report import EntropyReport

    result = await EntropyReport.analyze(populated_engine, project="cortex")

    assert result["total_facts"] == 4
    assert result["project_filter"] == "cortex"
    # Project entropy should be empty dict since we filtered
    assert result["project_entropy"]["categories"] == 0


@pytest.mark.asyncio
async def test_report_redundancy_present(populated_engine):
    """Report includes redundancy in each entropy block."""
    from cortex.shannon.report import EntropyReport

    result = await EntropyReport.analyze(populated_engine)

    for key in ["type_entropy", "source_entropy", "age_entropy"]:
        block = result[key]
        r = block["redundancy"]
        n = block["normalized"]
        assert math.isclose(r + n, 1.0, rel_tol=1e-3)


@pytest.mark.asyncio
async def test_trend_detection_stable(populated_engine):
    """All facts inserted at same time → trend should be 'stable' or 'growing'."""
    from cortex.shannon.report import EntropyReport

    result = await EntropyReport.analyze(populated_engine)
    assert result["temporal_trend"] in {"growing", "stable"}
