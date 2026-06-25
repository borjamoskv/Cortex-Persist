# [C5-REAL] Exergy-Maximized
"""
Stripe Billing Routes.

Full checkout flow: session creation, webhook processing, customer portal.
Provisions API keys automatically on successful payment.

Usage:
    Registered opt-in in api.py when STRIPE_SECRET_KEY is set.

Environment variables:
    STRIPE_SECRET_KEY - sk_live_... or sk_test_...
    STRIPE_WEBHOOK_SECRET - whsec_... from Stripe dashboard
    STRIPE_PRICE_TABLE - JSON mapping plan names to Stripe Price IDs
"""

import hashlib
import logging
import os
import time

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from legacy_research import config

__all__ = [
    "CheckoutRequest",
    "PortalRequest",
    "create_checkout_session",
    "create_portal_session",
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
    },
    "team": {
        "calls_limit": 500_000,
        "projects_limit": -1,  # unlimited
        "permissions": ["read", "write", "admin"],
        "rate_limit": 1000,
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
    seed = f"{email}:{plan}:{time.monotonic()}:{os.urandom(16).hex()}"
    return "ctx_" + hashlib.sha256(seed.encode()).hexdigest()[:48]


# ─── Routes ──────────────────────────────────────────────────────────


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
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": body.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": body.cancel_url,
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

    # ── Enqueue event into Immutable Ledger ──
    from legacy_research.ledger.billing_gateway import get_billing_gateway
    await get_billing_gateway().append_billing_event(event_type, event) # type: ignore

    return {"status": "enqueued", "type": event_type}


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
