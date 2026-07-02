# [C5-REAL] Exergy-Maximized
"""
Tenant Quota & Rate Limit Guard.

Provides O(1) Redis-backed atomic verification for billing rate limits
and consumption quotas per tenant. Enforces Zero-Anergy fail-fast.
"""

import time
from datetime import datetime, timezone

from fastapi import HTTPException

from babylon60.cache.redis_l1 import RedisL1Cache
from babylon60.routes.stripe import PLAN_CONFIG


class TenantGuard:
    """O(1) Rate Limit and Quota enforcement engine."""

    def __init__(self) -> None:
        self.cache = RedisL1Cache.singleton()
        # Fallback in-memory tracking if Redis is unavailable
        self._local_counts: dict[str, dict[str, float]] = {}

    def _get_local_incr(self, key: str, amount: int, ttl: int) -> int:
        now = time.time()
        if key not in self._local_counts:
            self._local_counts[key] = {"count": 0, "expires_at": now + ttl}
        else:
            if now > self._local_counts[key]["expires_at"]:
                self._local_counts[key] = {"count": 0, "expires_at": now + ttl}

        self._local_counts[key]["count"] += amount
        return int(self._local_counts[key]["count"])

    def verify_request(self, tenant_id: str, plan_name: str = "pro", ssu_cost: int = 1) -> None:
        """Verifies rate limits and quota. Raises HTTPException if exceeded.

        Args:
            tenant_id: The ID of the tenant.
            plan_name: The subscription plan name (default 'pro').
            ssu_cost: The cost of the operation in SSU units.
        """
        plan_limits = PLAN_CONFIG.get(plan_name)
        if not plan_limits:
            raise HTTPException(status_code=400, detail="Unknown subscription plan.")

        rate_limit = plan_limits["rate_limit"]
        calls_limit = plan_limits["calls_limit"]

        # 1. Check Rate Limit (requests per minute window)
        current_minute = int(time.time() // 60)
        rate_key = f"rate_limit:{tenant_id}:{current_minute}"

        count = self.cache.incr(rate_key, 1, ttl=60)
        if count is None:
            # Fallback to local memory if Redis is unavailable
            count = self._get_local_incr(rate_key, 1, ttl=60)

        if count > rate_limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Plan '{plan_name}' allows {rate_limit} req/min.",
            )

        # 2. Check Monthly Quota (SSU limits per month)
        # We skip checking if calls_limit is -1 (unlimited)
        if calls_limit != -1:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            quota_key = f"quota:{tenant_id}:{current_month}"

            # 31 days ttl ~ 2678400 seconds
            used_quota = self.cache.incr(quota_key, ssu_cost, ttl=2678400)
            if used_quota is None:
                used_quota = self._get_local_incr(quota_key, ssu_cost, ttl=2678400)

            if used_quota > calls_limit:
                raise HTTPException(
                    status_code=402,
                    detail=f"Monthly quota exhausted. Plan '{plan_name}' limit: {calls_limit}.",
                )


# Default singleton guard
tenant_guard = TenantGuard()
