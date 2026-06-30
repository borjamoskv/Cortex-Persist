# [C5-REAL] Exergy-Maximized
"""
Test suite for SubstackCrawlerGuard (Axiom OUROBOROS-014, OUROBOROS-094).
Validates epistemic rigidity against Bot Inflation and Sensor Drift.
"""

import pytest
from babylon60.guards.substack_crawler_guard import SubstackCrawlerGuard


@pytest.fixture
def guard() -> SubstackCrawlerGuard:
    return SubstackCrawlerGuard()


def test_nominal_sota_human(guard: SubstackCrawlerGuard) -> None:
    """Verifies that a genuine B2B institutional node passes with perfect exergy."""
    score = guard.evaluate_subscriber_exergy(
        email="borja@sohoradiolondon.com",
        opens=5,
        clicks=2,
        ts_delta_ms=5000.0,  # Human reaction time (5s)
    )
    assert score == 1.0


def test_sovereign_whitelist_bypass(guard: SubstackCrawlerGuard) -> None:
    """Verifies that known top organic humans bypass B2C domain filters and get perfect exergy."""
    score = guard.evaluate_subscriber_exergy(email="hugopotxo@gmail.com", opens=12, clicks=1)
    assert score == 1.0


def test_dead_inbox_crawler_inflation(guard: SubstackCrawlerGuard) -> None:
    """Verifies that PR inboxes with high opens are aborted as crawler inflation."""
    with pytest.raises(ValueError, match="OUROBOROS-094"):
        guard.evaluate_subscriber_exergy(email="editorial@hypebeast.com", opens=1556, clicks=1583)


def test_microsecond_scanner_detection(guard: SubstackCrawlerGuard) -> None:
    """Verifies that non-human reaction times (Firewalls) trigger epistemic breach."""
    with pytest.raises(ValueError, match="OUROBOROS-014"):
        guard.evaluate_subscriber_exergy(
            email="john.doe@corporate.com",
            opens=2,
            clicks=1,
            ts_delta_ms=50.0,  # 50ms is impossible for a human
        )


def test_symmetrical_engagement_anomaly(guard: SubstackCrawlerGuard) -> None:
    """Verifies that algorithmic 1:1 open/click ratios on high volume trigger abort."""
    with pytest.raises(ValueError, match="OUROBOROS-094"):
        guard.evaluate_subscriber_exergy(email="scanner@proofpoint.com", opens=100, clicks=98)


def test_malformed_identity(guard: SubstackCrawlerGuard) -> None:
    """Verifies that malformed emails trigger immediate epistemic breach."""
    with pytest.raises(ValueError, match="OUROBOROS-014"):
        guard.evaluate_subscriber_exergy(email="invalid_email_string", opens=0, clicks=0)
