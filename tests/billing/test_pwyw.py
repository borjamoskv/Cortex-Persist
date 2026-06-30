# [C5-REAL] Exergy-Maximized
"""CORTEX PWYW Billing & Quota - Test Suite.

Verifies dynamic checkout creation, free tier bypass, proportional quota calculations,
and dynamic enforcer check integrations.
"""

from __future__ import annotations

import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock

from babylon60.core import config
from babylon60.routes.stripe import CheckoutRequest, create_checkout_session
from babylon60.ledger.billing_gateway import BillingIntegrityGateway
from babylon60.extensions.metering.quotas import PlanQuota, QuotaEnforcer
from babylon60.extensions.metering.tracker import UsageTracker, UsageRecord


@pytest.fixture
def tmp_db():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


# ─── Checkout tests ──────────────────────────────────────────────────


def test_checkout_request_validation():
    """CheckoutRequest model should validate amount_usd and recurring fields."""
    req = CheckoutRequest(
        plan="pwyw",
        amount_usd=15.50,
        recurring=True,
    )
    assert req.amount_usd == 15.50
    assert req.recurring is True


@pytest.mark.asyncio
async def test_checkout_free_bypass():
    """Checkout with $0 amount should bypass Stripe and return free bypass metadata."""
    req = CheckoutRequest(
        plan="pwyw",
        amount_usd=0.00,
    )
    res = await create_checkout_session(req)
    assert res["session_id"] == "free_bypass"
    assert res["client_secret"] is None
    assert "session_id=free_bypass" in res["url"]


@pytest.mark.asyncio
async def test_checkout_dynamic_price_data(monkeypatch):
    """Checkout with custom amount should create a session using dynamic price_data."""
    mock_stripe = MagicMock()
    mock_session = MagicMock()
    mock_session.client_secret = "secret_123"
    mock_session.id = "sess_123"
    mock_session.url = "https://checkout.stripe.com/sess_123"
    mock_stripe.checkout.Session.create.return_value = mock_session

    import babylon60.routes.stripe as stripe_module

    monkeypatch.setattr(stripe_module, "config", config)
    monkeypatch.setattr(stripe_module, "_get_stripe", lambda: mock_stripe)

    req = CheckoutRequest(
        plan="pwyw",
        amount_usd=25.00,
        recurring=True,
    )
    res = await create_checkout_session(req)

    assert res["client_secret"] == "secret_123"
    assert res["session_id"] == "sess_123"
    assert res["url"] == "https://checkout.stripe.com/sess_123"

    mock_stripe.checkout.Session.create.assert_called_once()
    called_args = mock_stripe.checkout.Session.create.call_args[1]
    assert called_args["mode"] == "subscription"
    assert called_args["metadata"]["plan"] == "pwyw"
    assert called_args["metadata"]["amount_usd"] == "25.0"

    line_items = called_args["line_items"]
    assert line_items[0]["price_data"]["unit_amount"] == 2500
    assert line_items[0]["price_data"]["recurring"] == {"interval": "month"}
    assert (
        line_items[0]["price_data"]["product_data"]["name"]
        == "CORTEX Proportional Quota Contribution"
    )


# ─── Billing Gateway & Quota Scaling Tests ──────────────────────────


@pytest.mark.asyncio
async def test_billing_gateway_pwyw_scaling(tmp_db, monkeypatch):
    """BillingIntegrityGateway should scale quota limits based on paid amount."""
    import aiosqlite
    from babylon60.database.schema import CREATE_TENANTS

    async with aiosqlite.connect(tmp_db) as conn:
        await conn.execute(CREATE_TENANTS)
        await conn.commit()

    gateway = BillingIntegrityGateway(db_path=tmp_db)
    await gateway.initialize()

    # Mock auth manager key creation
    mock_auth_manager = AsyncMock()
    import babylon60.api.state as api_state_b60
    import babylon60.api.state as api_state_ctx

    monkeypatch.setattr(api_state_b60, "auth_manager", mock_auth_manager)
    monkeypatch.setattr(api_state_ctx, "auth_manager", mock_auth_manager)

    # Mock stripe key configuration
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "sk_test_mock_123")

    payload = {
        "data": {
            "object": {
                "customer_email": "test-pwyw@cortex.com",
                "subscription": "sub_123",
                "metadata": {
                    "plan": "pwyw",
                    "amount_usd": "15.00",
                },
            }
        }
    }

    # Execute webhook handler event directly
    await gateway._handle_event("checkout.session.completed", payload)

    # Assert AuthManager created a key with proportional rate limit: 30 + 15 * 5 = 105
    mock_auth_manager.create_key.assert_called_once()
    key_kwargs = mock_auth_manager.create_key.call_args[1]
    assert key_kwargs["tenant_id"] == "test-pwyw@cortex.com"
    assert key_kwargs["rate_limit"] == 105

    # Assert the database contains the correct scaled quotas inside the tenant config
    import aiosqlite

    async with aiosqlite.connect(tmp_db) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT config FROM tenants WHERE id = ?", ("test-pwyw@cortex.com",)
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            import json

            config_data = json.loads(row["config"])
            assert config_data["plan"] == "pwyw"
            assert config_data["amount_usd"] == 15.00
            # Scaled limit: 15.00 * 10000 = 150000
            assert config_data["calls_limit"] == 150000
            assert config_data["rate_limit"] == 105
            assert config_data["projects_limit"] == 7
            assert config_data["storage_bytes"] == 1500 * 1024 * 1024


# ─── QuotaEnforcer Dynamic check tests ──────────────────────────────


def test_quota_enforcer_with_custom_quota(tmp_db):
    """QuotaEnforcer should evaluate dynamic PlanQuota correctly."""
    tracker = UsageTracker(db_path=tmp_db)
    enforcer = QuotaEnforcer(tracker)

    # 1. Custom quota: 5,000 calls
    custom_quota = PlanQuota(
        name="pwyw",
        calls_limit=5000,
        projects_limit=2,
        storage_bytes=50 * 1024 * 1024,
        rate_limit=100,
        search_depth=3,
        batch_size=50,
        ledger_verify=True,
    )

    # 2. Assert allowed under limit
    res1 = enforcer.check_with_quota("pwyw-tenant", custom_quota)
    assert res1.allowed is True
    assert res1.limit == 5000
    assert res1.remaining == 5000

    # 3. Simulate usage exceeding limit
    for _ in range(5000):
        tracker.record(UsageRecord(tenant_id="pwyw-tenant", endpoint="/v1/facts", method="POST"))

    res2 = enforcer.check_with_quota("pwyw-tenant", custom_quota)
    assert res2.allowed is False
    assert res2.remaining == 0

    tracker.close()
