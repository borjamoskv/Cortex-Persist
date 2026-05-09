from typing import Optional

"""
CORTEX v5.0 — Stripe Billing Routes.

Full checkout flow: session creation, webhook processing, customer portal.
Provisions API keys automatically on successful payment.

Usage:
    Registered opt-in in api.py when STRIPE_SECRET_KEY is set.

Environment variables:
    STRIPE_SECRET_KEY — Stripe secret key (from dashboard.stripe.com/apikeys)
    STRIPE_WEBHOOK_SECRET — Stripe webhook signing secret (from dashboard)
    STRIPE_PRICE_TABLE — JSON mapping plan names to Stripe Price IDs
"""

import hashlib
import logging
import os
import time

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from cortex import config

__all__ = [
    "CheckoutRequest",
    "PortalRequest",
    "create_checkout_session",
    "create_portal_session",
    "get_stripe_config",
    "stripe_webhook",
]

router = APIRouter(prefix="/v1/stripe", tags=["stripe"])
logger = logging.getLogger("uvicorn.error")

# ─── Plan Configuration ──────────────────────────────────────────────

PLAN_CONFIG: dict[str, dict] = {
    "pro": {
        "calls_limit": 50_000,
        "projects_limit": 10,
        "permissions": ["read", "write"],
        "rate_limit": 300,
        "display_name": "Pro Plan",
        "default_price": "$29",
        "interval": "month",
    },
    "team": {
        "calls_limit": 500_000,
        "projects_limit": -1,  # unlimited
        "permissions": ["read", "write", "admin"],
        "rate_limit": 1000,
        "display_name": "Team Plan",
        "default_price": "$99",
        "interval": "month",
    },
}


# ─── Request Models ──────────────────────────────────────────────────


class CheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session."""

    plan: str = "pro"
    customer_email: str | None = None
    success_url: str = "https://cortexpersist.com"
    cancel_url: str = "https://cortexpersist.com"


class PortalRequest(BaseModel):
    """Request to create a Stripe Customer Portal session."""

    customer_id: str
    return_url: str = "https://cortexpersist.com"


# ─── Helpers ─────────────────────────────────────────────────────────


def _get_stripe():
    """Lazy-import and configure Stripe SDK."""
    try:
        import stripe
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="stripe package not installed. Install with: pip install stripe",
        ) from exc

    stripe.api_key = config.STRIPE_SECRET_KEY  # type: ignore[reportAttributeAccessIssue]
    return stripe


def _generate_api_key(email: str, plan: str) -> str:
    """Generate a unique API key with ctx_ prefix."""
    seed = f"{email}:{plan}:{time.time()}:{os.urandom(16).hex()}"
    return "ctx_" + hashlib.sha256(seed.encode()).hexdigest()[:48]


async def _provision_api_key(email: str, plan: str) -> Optional[str]:
    """Create an API key in CORTEX AuthManager. Returns raw key or None."""
    raw_key = _generate_api_key(email, plan)
    plan_cfg = PLAN_CONFIG.get(plan, PLAN_CONFIG["pro"])

    try:
        import cortex.api.state as api_state

        if api_state.auth_manager:
            await api_state.auth_manager.create_key(
                name=f"stripe-{email}",
                tenant_id=email,
                permissions=plan_cfg["permissions"],
                rate_limit=plan_cfg["rate_limit"],
            )
            logger.info(
                "API key provisioned: %s → %s plan (prefix: %s...)",
                email,
                plan,
                raw_key[:12],
            )
            return raw_key
    except (RuntimeError, ValueError, OSError):
        logger.exception("Failed to provision API key for %s", email)

    return None


async def _revoke_keys_for_email(email: str) -> None:
    """Find and revoke Stripe API keys for an email."""
    try:
        import cortex.api.state as api_state

        if api_state.auth_manager:
            keys = await api_state.auth_manager.list_keys(tenant_id=email)
            for key in keys:
                if key.name.startswith("stripe-"):
                    await api_state.auth_manager.revoke_key(key.id)
                    logger.info("Revoked key %s for cancelled subscription", key.name)
    except (RuntimeError, ValueError, OSError):
        logger.exception("Failed to revoke keys for email %s", email)


# ─── Routes ──────────────────────────────────────────────────────────


@router.get("/config")
async def get_stripe_config() -> dict:
    """Return public Stripe configuration for the frontend.

    Exposes the publishable key and plan display prices.
    Never exposes secret keys or webhook secrets.
    """
    public_key = config.STRIPE_PUBLIC_KEY  # type: ignore[reportAttributeAccessIssue]
    price_table = config.STRIPE_PRICE_TABLE

    plans: dict[str, dict] = {}
    for plan_name, plan_cfg in PLAN_CONFIG.items():
        plan_entry: dict[str, str] = {
            "name": plan_cfg["display_name"],
            "price": plan_cfg["default_price"],
            "interval": plan_cfg["interval"],
        }

        # Attempt live price lookup from Stripe if configured
        price_id = price_table.get(plan_name)
        if price_id and public_key:
            try:
                stripe_sdk = _get_stripe()
                price_obj = stripe_sdk.Price.retrieve(  # type: ignore
                    price_id
                )
                raw_amount = price_obj.unit_amount
                amount = raw_amount / 100 if raw_amount else 0
                currency = price_obj.currency.upper()
                symbol = "$" if currency == "USD" else f"{currency} "
                plan_entry["price"] = f"{symbol}{amount:g}"
                if price_obj.recurring:
                    plan_entry["interval"] = price_obj.recurring.interval
            except (RuntimeError, ValueError, OSError):
                logger.warning("Could not fetch live price for %s, using default", plan_name)

        plans[plan_name] = plan_entry

    return {
        "public_key": public_key,
        "plans": plans,
    }


@router.post("/checkout", include_in_schema=False)
async def create_checkout_session(body: CheckoutRequest) -> dict:
    """Create a Stripe Checkout session for a plan purchase."""
    stripe = _get_stripe()

    if body.plan not in PLAN_CONFIG:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown plan '{body.plan}'. Available: {list(PLAN_CONFIG.keys())}",
        )

    price_table = config.STRIPE_PRICE_TABLE
    price_id = price_table.get(body.plan)
    if not price_id:
        raise HTTPException(
            status_code=500,
            detail=f"No Stripe Price ID configured for plan '{body.plan}'. "
            "Set STRIPE_PRICE_TABLE env var.",
        )

    try:
        session_kwargs = {
            "mode": "subscription",
            "ui_mode": "embedded",
            "line_items": [{"price": price_id, "quantity": 1}],
            "return_url": body.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            "metadata": {"plan": body.plan},
        }
        if body.customer_email:
            session_kwargs["customer_email"] = body.customer_email

        # type: ignore[reportAttributeAccessIssue]
        session = stripe.checkout.Session.create(**session_kwargs)  # type: ignore[reportAttributeAccessIssue]
    except stripe.StripeError as exc:  # type: ignore[reportAttributeAccessIssue]
        logger.error("Stripe checkout error: %s", exc)
        raise HTTPException(status_code=502, detail="Stripe API error") from exc

    return {"client_secret": session.client_secret, "session_id": session.id, "url": session.url}


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
) -> dict:
    """Handle Stripe webhook events."""
    stripe = _get_stripe()
    webhook_secret = config.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    payload = await request.body()

    try:
        # type: ignore[reportAttributeAccessIssue]
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)  # type: ignore[reportAttributeAccessIssue]
    except stripe.SignatureVerificationError as exc:  # type: ignore[reportAttributeAccessIssue]
        raise HTTPException(status_code=400, detail="Invalid webhook signature") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid payload") from exc

    event_type = event["type"]

    # ── Checkout completed → provision API key ──
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_email") or session.get("customer_details", {}).get(
            "email", "unknown"
        )
        plan = session.get("metadata", {}).get("plan", "pro")

        raw_key = await _provision_api_key(customer_email, plan)

        return {
            "status": "provisioned",
            "email": customer_email,
            "plan": plan,
            "key_provisioned": raw_key is not None,
        }

    # ── Subscription cancelled → revoke API key ──
    if event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer", "")

        try:
            stripe_obj = _get_stripe()
            # type: ignore[reportAttributeAccessIssue]
            customer = stripe_obj.Customer.retrieve(customer_id)  # type: ignore[reportAttributeAccessIssue]
            email = customer.get("email", "")

            if email:
                await _revoke_keys_for_email(email)
        except (RuntimeError, ValueError, OSError):
            logger.exception("Failed to process revoked subscription for customer %s", customer_id)

        return {"status": "revoked", "customer": customer_id}

    # ── Unhandled event type ──
    logger.debug("Ignoring Stripe event: %s", event_type)
    return {"status": "ignored", "type": event_type}


@router.post("/portal", include_in_schema=False)
async def create_portal_session(body: PortalRequest) -> dict:
    """Create a Stripe Customer Portal session for billing management."""
    stripe = _get_stripe()

    try:
        session = stripe.billing_portal.Session.create(  # type: ignore[reportAttributeAccessIssue]
            customer=body.customer_id,
            return_url=body.return_url,
        )
    except stripe.StripeError as exc:  # type: ignore[reportAttributeAccessIssue]
        logger.error("Stripe portal error: %s", exc)
        raise HTTPException(status_code=502, detail="Stripe API error") from exc

    return {"url": session.url}
