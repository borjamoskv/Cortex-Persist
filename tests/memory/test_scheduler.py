# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""Tests for the MemoryScheduler module."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import pytest

from babylon60.memory.scheduler import MemoryScheduler, SchedulerConfig
from babylon60.extensions.hypervisor.belief_object import (
    BeliefConfidence,
    BeliefObject,
    BeliefStatus,
)


@dataclass
class MockBelief:
    """Mock belief object for testing fallback paths."""

    content: str
    proposition_key: str | None = None
    id: str | None = None
    confidence: Any = 0.5
    timestamp_last_verified: float | None = None
    created_at: str | None = None
    revised_at: str | None = None
    cost_tokens: float | None = None
    contamination_risk: float = 0.0
    status: str = "active"

    def is_quarantined(self) -> bool:
        return self.status == "quarantined"


def test_scheduler_config_defaults() -> None:
    """Test that SchedulerConfig has the correct defaults."""
    config = SchedulerConfig()
    assert config.w_relevance == 0.5
    assert config.w_confidence == 0.3
    assert config.w_recency == 0.2
    assert config.contamination_threshold == 0.7
    assert config.recency_decay_rate == 1e-6


def test_score_equation_with_mock_belief() -> None:
    """Test standard score calculations using a MockBelief."""
    config = SchedulerConfig(
        w_relevance=0.4,
        w_confidence=0.3,
        w_recency=0.3,
        contamination_threshold=0.8,
        recency_decay_rate=1e-5,
    )
    scheduler = MemoryScheduler(config)

    # Perfect fresh belief
    belief = MockBelief(
        content="Testing content scheduling",
        proposition_key="test.schedule",
        confidence=1.0,
        timestamp_last_verified=time.time(),
        cost_tokens=10.0,
        contamination_risk=0.1,
    )

    # 1. Relevance: Explicitly pass 1.0 relevance
    score = scheduler.score(belief, relevance=1.0, contamination_risk=0.1)

    # Expected calculation:
    # Rel = 1.0, Conf = 1.0, Rec = exp(-1e-5 * 0) = 1.0
    # Numerator = (1.0 * 0.4) + (1.0 * 0.3) + (1.0 * 0.3) = 1.0
    # Denominator = Cost_tokens + Risk_contam = 10.0 + 0.1 = 10.1
    # Expected score = 1.0 / 10.1 = 0.0990099...
    assert score == pytest.approx(1.0 / 10.1)


def test_score_relevance_graceful_fallback() -> None:
    """Test that relevance falls back to proposition_key hash when not provided."""
    scheduler = MemoryScheduler()
    belief = MockBelief(
        content="Test content",
        proposition_key="my.key",
        confidence=0.8,
        cost_tokens=5.0,
    )

    # Relevances should be different with different queries
    score_q1 = scheduler.score(belief, query="query1")
    score_q2 = scheduler.score(belief, query="query2")
    assert score_q1 != score_q2


def test_confidence_resolution() -> None:
    """Test confidence mapping from enums, strings and floats."""
    scheduler = MemoryScheduler()

    # Test float
    b_float = MockBelief(content="Test", confidence=0.7)
    assert scheduler._extract_confidence_value(b_float) == 0.7

    # Test Enum
    b_enum = MockBelief(content="Test", confidence=BeliefConfidence.C4_CONFIRMED)
    assert scheduler._extract_confidence_value(b_enum) == 0.8

    # Test String
    b_str = MockBelief(content="Test", confidence="C5")
    assert scheduler._extract_confidence_value(b_str) == 1.0

    # Test Unknown fallback
    b_unknown = MockBelief(content="Test", confidence="UNKNOWN")
    assert scheduler._extract_confidence_value(b_unknown) == 0.5


def test_recency_exponential_decay() -> None:
    """Test exponential decay on timestamps."""
    from unittest.mock import patch
    # Decay rate: 0.1 per second
    config = SchedulerConfig(recency_decay_rate=0.1)
    scheduler = MemoryScheduler(config)

    now = 1700000000.0
    with patch("time.time", return_value=now):
        b_fresh = MockBelief(content="Test", timestamp_last_verified=now)
        b_old = MockBelief(content="Test", timestamp_last_verified=now - 10.0)

        rec_fresh = scheduler._calculate_recency(b_fresh)
        rec_old = scheduler._calculate_recency(b_old)

        assert rec_fresh == pytest.approx(1.0, abs=1e-3)
        assert rec_old == pytest.approx(math.exp(-1.0), abs=1e-3)


def test_timestamp_parsing() -> None:
    """Test parsing of different timestamp formats (float, ISO string)."""
    scheduler = MemoryScheduler()

    # Float
    assert scheduler._parse_timestamp(123456789.0) == 123456789.0

    # ISO string UTC
    iso_str = "2026-06-30T00:00:00Z"
    expected = datetime.fromisoformat("2026-06-30T00:00:00+00:00").timestamp()
    assert scheduler._parse_timestamp(iso_str) == expected


def test_admit_logic() -> None:
    """Test admission checks for contamination risk and quarantine status."""
    scheduler = MemoryScheduler(SchedulerConfig(contamination_threshold=0.6))

    # Allowed belief
    b_ok = MockBelief(content="Ok", contamination_risk=0.3)
    assert scheduler.admit(b_ok) is True

    # Rejected contamination risk
    b_high_risk = MockBelief(content="Risk", contamination_risk=0.8)
    assert scheduler.admit(b_high_risk) is False

    # Rejected quarantined status
    b_quarantined = MockBelief(content="Quarantined", status="quarantined")
    assert scheduler.admit(b_quarantined) is False


def test_rank_beliefs_with_budget() -> None:
    """Test ranking and sorting of beliefs within token budgets."""
    scheduler = MemoryScheduler()

    b1 = MockBelief(content="Small", cost_tokens=2.0, confidence=1.0)
    b2 = MockBelief(content="Medium", cost_tokens=5.0, confidence=0.8)
    b3 = MockBelief(content="Large", cost_tokens=10.0, confidence=0.6)

    beliefs = [b3, b1, b2]

    # Without budget, all should be returned sorted by score
    # Score calculation ensures higher confidence has higher score
    ranked_no_budget = scheduler.rank_beliefs(beliefs, query="test")
    assert len(ranked_no_budget) == 3
    # b1 has highest confidence and lowest cost -> should be first
    assert ranked_no_budget[0] == b1
    assert ranked_no_budget[1] == b2
    assert ranked_no_budget[2] == b3

    # With budget of 8 tokens
    ranked_budget = scheduler.rank_beliefs(beliefs, query="test", token_budget=8)
    assert len(ranked_budget) == 2
    assert ranked_budget[0] == b1  # cost 2
    assert ranked_budget[1] == b2  # cost 5 (cumulative = 7 <= 8)


def test_real_belief_object_integration() -> None:
    """Test integration directly with real BeliefObject from babylon60."""
    scheduler = MemoryScheduler()

    belief = BeliefObject(
        content="Sovereign memory scheduling is functional",
        project="cortex-unit-test",
        confidence=BeliefConfidence.C4_CONFIRMED,
        created_at="2026-06-30T00:00:00Z",
    )

    score = scheduler.score(belief, query="scheduler")
    assert score > 0.0
    assert scheduler.admit(belief) is True
