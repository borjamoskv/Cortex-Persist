"""Tests for cortex.metering module — tracker, quotas, and middleware."""

import os
import tempfile

import pytest

from cortex.extensions.metering.quotas import PLAN_QUOTAS, QuotaEnforcer
from cortex.extensions.metering.tracker import UsageRecord, UsageTracker

# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def tmp_db():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def tracker(tmp_db):
    """Create a UsageTracker with a temp DB."""
    t = UsageTracker(db_path=tmp_db)
    yield t
    t.close()


@pytest.fixture
def enforcer(tracker):
    """Create a QuotaEnforcer backed by the test tracker."""
    return QuotaEnforcer(tracker)


# ─── UsageTracker Tests ─────────────────────────────────────────────


class TestUsageTracker:
    """Tests for the UsageTracker class."""

    def test_record_and_get_usage(self, tracker):
        """Recording a call should increment usage counters."""
        record = UsageRecord(
            tenant_id="test-tenant",
            endpoint="/v1/memories",
            method="POST",
            status_code=200,
        )
        tracker.record(record)

        usage = tracker.get_usage("test-tenant")
        assert usage["calls_used"] == 1
        assert usage["tokens_used"] == 0

    def test_multiple_records_aggregate(self, tracker):
        """Multiple records should accumulate in monthly summary."""
        for _i in range(5):
            tracker.record(
                UsageRecord(
                    tenant_id="tenant-a",
                    endpoint="/v1/memories",
                    method="POST",
                    tokens_used=10,
                )
            )

        usage = tracker.get_usage("tenant-a")
        assert usage["calls_used"] == 5
        assert usage["tokens_used"] == 50

    def test_tenant_isolation(self, tracker):
        """Usage should be isolated per tenant."""
        tracker.record(UsageRecord(tenant_id="alice", endpoint="/v1/memories", method="POST"))
        tracker.record(UsageRecord(tenant_id="bob", endpoint="/v1/search", method="POST"))
        tracker.record(UsageRecord(tenant_id="bob", endpoint="/v1/search", method="POST"))

        assert tracker.get_usage("alice")["calls_used"] == 1
        assert tracker.get_usage("bob")["calls_used"] == 2

    def test_empty_usage(self, tracker):
        """Non-existent tenant should return zero usage."""
        usage = tracker.get_usage("nonexistent")
        assert usage["calls_used"] == 0
        assert usage["last_call_at"] is None

    def test_usage_history(self, tracker):
        """History should return list of month records."""
        tracker.record(UsageRecord(tenant_id="t1", endpoint="/v1/memories", method="POST"))
        history = tracker.get_usage_history("t1")
        assert len(history) >= 1
        assert history[0]["calls_used"] == 1

    def test_endpoint_breakdown(self, tracker):
        """Breakdown should group by endpoint and method."""
        for _ in range(3):
            tracker.record(UsageRecord(tenant_id="t1", endpoint="/v1/memories", method="POST"))
        for _ in range(2):
            tracker.record(
                UsageRecord(tenant_id="t1", endpoint="/v1/memories/search", method="POST")
            )

        breakdown = tracker.get_endpoint_breakdown("t1")
        assert len(breakdown) == 2
        # Ordered by calls DESC
        assert breakdown[0]["calls"] == 3
        assert breakdown[1]["calls"] == 2


# ─── QuotaEnforcer Tests ────────────────────────────────────────────


class TestQuotaEnforcer:
    """Tests for the QuotaEnforcer class."""

    def test_free_tier_allows_under_limit(self, enforcer, tracker):
        """Free tier should allow calls within the 1000 limit."""
        result = enforcer.check("new-tenant", "free")
        assert result.allowed is True
        assert result.remaining == 1000
        assert result.limit == 1000

    def test_free_tier_blocks_over_limit(self, enforcer, tracker):
        """Free tier should block after 1000 calls."""
        for _ in range(1000):
            tracker.record(
                UsageRecord(tenant_id="heavy-user", endpoint="/v1/memories", method="POST")
            )

        result = enforcer.check("heavy-user", "free")
        assert result.allowed is False
        assert result.remaining == 0

    def test_pro_tier_higher_limit(self, enforcer):
        """Pro tier should have 50,000 call limit."""
        result = enforcer.check("pro-user", "pro")
        assert result.allowed is True
        assert result.limit == 50_000

    def test_team_tier_high_limit(self, enforcer, tracker):
        """Team tier should have high call limit (500K)."""
        for _ in range(100):
            tracker.record(
                UsageRecord(tenant_id="team-user", endpoint="/v1/memories", method="POST")
            )

        result = enforcer.check("team-user", "team")
        assert result.allowed is True
        assert result.remaining == 500_000 - 100
        assert result.limit == 500_000

    def test_unknown_plan_defaults_to_free(self, enforcer):
        """Unknown plan should default to free tier limits."""
        result = enforcer.check("unknown", "nonexistent-plan")
        assert result.limit == 1000

    def test_plan_info(self, enforcer):
        """Plan info should return correct quota details."""
        info = enforcer.get_plan_info("pro")
        assert info["calls_limit"] == 50_000
        assert info["projects_limit"] == 10
        assert info["rate_limit"] == 300
        assert info["ledger_verify"] is True


# ─── Plan Definitions Tests ─────────────────────────────────────────


class TestPlanQuotas:
    """Tests for plan quota definitions."""

    def test_three_plans_defined(self):
        """Should have exactly 3 plans: free, pro, team."""
        assert set(PLAN_QUOTAS.keys()) == {"free", "pro", "team"}

    def test_free_plan_limits(self):
        """Free plan should have conservative limits."""
        free = PLAN_QUOTAS["free"]
        assert free.calls_limit == 1_000
        assert free.projects_limit == 1
        assert free.rate_limit == 30
        assert free.ledger_verify is False

    def test_plans_are_frozen(self):
        """Plan quotas should be immutable."""
        with pytest.raises(AttributeError):
            PLAN_QUOTAS["free"].calls_limit = 999  # type: ignore
