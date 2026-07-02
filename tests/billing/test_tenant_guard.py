# [C5-REAL] Exergy-Maximized
import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock

from babylon60.api.tenant_guard import TenantGuard


@pytest.fixture
def guard():
    # Use isolated local counts for tests
    g = TenantGuard()
    g._local_counts = {}

    # Mock Redis so we always use local fallback logic which is deterministic
    mock_cache = MagicMock()
    mock_cache.incr.return_value = None
    g.cache = mock_cache

    return g


def test_tenant_guard_unknown_plan(guard):
    """It should raise 400 for unknown plans."""
    with pytest.raises(HTTPException) as exc:
        guard.verify_request("tenant_123", plan_name="unknown_plan")
    assert exc.value.status_code == 400
    assert "Unknown subscription plan" in exc.value.detail


def test_tenant_guard_rate_limit_pro(guard):
    """Pro plan allows 300 req/min. 301st should fail with 429."""
    for _ in range(300):
        guard.verify_request("tenant_rate", plan_name="pro")

    with pytest.raises(HTTPException) as exc:
        guard.verify_request("tenant_rate", plan_name="pro")
    assert exc.value.status_code == 429
    assert "Rate limit exceeded" in exc.value.detail


def test_tenant_guard_quota_exhaustion_pro(guard):
    """Pro plan allows 50,000 requests per month. Simulate hitting it."""
    # We can fake the current count by artificially injecting to the dict
    import time
    from datetime import datetime, timezone

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    quota_key = f"quota:tenant_quota:{current_month}"

    # Manually set the local memory counter to 49,999
    guard._local_counts[quota_key] = {"count": 49999, "expires_at": time.time() + 10000}

    # The 50,000th request should pass
    guard.verify_request("tenant_quota", plan_name="pro")

    # The 50,001st request should fail
    with pytest.raises(HTTPException) as exc:
        guard.verify_request("tenant_quota", plan_name="pro")
    assert exc.value.status_code == 402
    assert "Monthly quota exhausted" in exc.value.detail


def test_tenant_guard_high_quota_team(guard):
    """Team plan has calls_limit = 500,000. Verify boundary."""
    import time
    from datetime import datetime, timezone

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    quota_key = f"quota:tenant_team:{current_month}"

    # Manually set count to just below the limit
    guard._local_counts[quota_key] = {"count": 499999, "expires_at": time.time() + 10000}

    # We mock rate limit key to not hit 429
    current_minute = int(time.time() // 60)
    rate_key = f"rate_limit:tenant_team:{current_minute}"
    guard._local_counts[rate_key] = {"count": 0, "expires_at": time.time() + 100}

    # This should pass without raising 402
    guard.verify_request("tenant_team", plan_name="team")
