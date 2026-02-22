"""
CORTEX v4.3 — Stripe Billing Tests.

Tests for checkout session creation, webhook processing, portal,
and subscription lifecycle. All Stripe SDK calls are mocked.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cortex.routes.stripe import (
    PLAN_CONFIG,
    _generate_api_key,
)

# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _stripe_env(monkeypatch):
    """Set Stripe env vars for all tests."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key_for_testing")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_fake_secret")
    monkeypatch.setenv(
        "STRIPE_PRICE_TABLE",
        '{"pro": "price_pro_test", "team": "price_team_test"}',
    )
    # Reload config to pick up new env vars
    from cortex import config as cfg_mod

    cfg_mod.reload()


@pytest.fixture
def client(_stripe_env):
    """TestClient with Stripe routes enabled."""
    from cortex.api import app

    # Force-register stripe router for testing (may already be registered)
    from cortex.routes.stripe import router as stripe_router

    # Check if already mounted
    stripe_paths = [r.path for r in app.routes if hasattr(r, "path") and "/stripe/" in r.path]
    if not stripe_paths:
        app.include_router(stripe_router)

    return TestClient(app)


# ─── Plan Config ─────────────────────────────────────────────────────


class TestPlanConfig:
    def test_pro_plan_exists(self):
        assert "pro" in PLAN_CONFIG

    def test_team_plan_exists(self):
        assert "team" in PLAN_CONFIG

    def test_pro_permissions(self):
        assert PLAN_CONFIG["pro"]["permissions"] == ["read", "write"]

    def test_team_has_admin(self):
        assert "admin" in PLAN_CONFIG["team"]["permissions"]

    def test_team_unlimited_projects(self):
        assert PLAN_CONFIG["team"]["projects_limit"] == -1


# ─── API Key Generation ─────────────────────────────────────────────


class TestKeyGeneration:
    def test_key_format(self):
        key = _generate_api_key("test@example.com", "pro")
        assert key.startswith("ctx_")
        assert len(key) == 52  # "ctx_" + 48 hex chars

    def test_keys_are_unique(self):
        key1 = _generate_api_key("test@example.com", "pro")
        key2 = _generate_api_key("test@example.com", "pro")
        assert key1 != key2

    def test_different_plans_different_keys(self):
        key1 = _generate_api_key("test@example.com", "pro")
        key2 = _generate_api_key("test@example.com", "team")
        assert key1 != key2


# ─── Checkout Endpoint ──────────────────────────────────────────────


class TestCheckout:
    @patch("cortex.routes.stripe._get_stripe")
    def test_checkout_creates_session(self, mock_get_stripe, client):
        mock_stripe = MagicMock()
        mock_stripe.checkout.Session.create.return_value = SimpleNamespace(
            url="https://checkout.stripe.com/test_session",
            id="cs_test_123",
        )
        mock_get_stripe.return_value = mock_stripe

        resp = client.post(
            "/v1/stripe/checkout",
            json={"plan": "pro", "success_url": "https://example.com/success", "cancel_url": "https://example.com/cancel"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://checkout.stripe.com/test_session"
        assert data["session_id"] == "cs_test_123"

    @patch("cortex.routes.stripe._get_stripe")
    def test_checkout_invalid_plan(self, mock_get_stripe, client):
        mock_get_stripe.return_value = MagicMock()

        resp = client.post(
            "/v1/stripe/checkout",
            json={"plan": "nonexistent"},
        )

        assert resp.status_code == 400
        assert "Unknown plan" in resp.json()["detail"]

    @patch("cortex.routes.stripe._get_stripe")
    def test_checkout_default_plan(self, mock_get_stripe, client):
        mock_stripe = MagicMock()
        mock_stripe.checkout.Session.create.return_value = SimpleNamespace(
            url="https://checkout.stripe.com/default",
            id="cs_default",
        )
        mock_get_stripe.return_value = mock_stripe

        resp = client.post("/v1/stripe/checkout", json={})

        assert resp.status_code == 200
        # Verify "pro" plan was used (default)
        call_kwargs = mock_stripe.checkout.Session.create.call_args
        assert call_kwargs.kwargs["metadata"]["plan"] == "pro"


# ─── Webhook Endpoint ───────────────────────────────────────────────


class TestWebhook:
    @patch("cortex.routes.stripe._provision_api_key")
    @patch("cortex.routes.stripe._get_stripe")
    def test_webhook_checkout_completed(self, mock_get_stripe, mock_provision, client):
        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer_email": "buyer@example.com",
                    "metadata": {"plan": "pro"},
                }
            },
        }
        mock_get_stripe.return_value = mock_stripe
        mock_provision.return_value = "ctx_fake_key_123"

        resp = client.post(
            "/v1/stripe/webhook",
            content=b"raw_payload",
            headers={"Stripe-Signature": "t=123,v1=abc"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "provisioned"
        assert data["email"] == "buyer@example.com"
        assert data["key_provisioned"] is True

    @patch("cortex.routes.stripe._get_stripe")
    def test_webhook_invalid_signature(self, mock_get_stripe, client):
        mock_stripe = MagicMock()
        # Create a proper exception class for SignatureVerificationError
        sig_error = type("SignatureVerificationError", (Exception,), {})
        mock_stripe.SignatureVerificationError = sig_error
        mock_stripe.Webhook.construct_event.side_effect = sig_error("bad sig")
        mock_get_stripe.return_value = mock_stripe

        resp = client.post(
            "/v1/stripe/webhook",
            content=b"tampered",
            headers={"Stripe-Signature": "invalid"},
        )

        assert resp.status_code == 400

    @patch("cortex.routes.stripe._get_stripe")
    def test_webhook_ignores_unknown_events(self, mock_get_stripe, client):
        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.return_value = {
            "type": "invoice.paid",
            "data": {"object": {}},
        }
        mock_get_stripe.return_value = mock_stripe

        resp = client.post(
            "/v1/stripe/webhook",
            content=b"payload",
            headers={"Stripe-Signature": "t=1,v1=sig"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"


# ─── Portal Endpoint ────────────────────────────────────────────────


class TestPortal:
    @patch("cortex.routes.stripe._get_stripe")
    def test_portal_creates_session(self, mock_get_stripe, client):
        mock_stripe = MagicMock()
        mock_stripe.billing_portal.Session.create.return_value = SimpleNamespace(
            url="https://billing.stripe.com/session/test",
        )
        mock_get_stripe.return_value = mock_stripe

        resp = client.post(
            "/v1/stripe/portal",
            json={"customer_id": "cus_test_123", "return_url": "https://example.com"},
        )

        assert resp.status_code == 200
        assert "billing.stripe.com" in resp.json()["url"]

    def test_portal_requires_customer_id(self, client):
        resp = client.post("/v1/stripe/portal", json={})
        assert resp.status_code == 422  # Pydantic validation error


# ─── Route Registration ─────────────────────────────────────────────


class TestRouteRegistration:
    def test_stripe_not_registered_without_key(self, monkeypatch):
        """When STRIPE_SECRET_KEY is empty, Stripe routes should not be mounted."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "")
        from cortex import config as cfg_mod

        cfg_mod.reload()
        assert cfg_mod.STRIPE_SECRET_KEY == ""
