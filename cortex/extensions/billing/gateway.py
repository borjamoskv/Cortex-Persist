# [C5-REAL] Exergy-Maximized
"""CORTEX Billing Gateway - Stripe Integration.

Integrates SaaS subscription management, metered usage reporting,
and automated revenue quarantine logic for F2 (adversarial) events.
"""

from __future__ import annotations

import logging
from typing import Any

from stripe_config import StripeBillingConfig, load_stripe_billing_config
from cortex.extensions.billing.models import BillingEvent, FailureType

logger = logging.getLogger(__name__)

try:
    import stripe
except ImportError:
    stripe = None  # type: ignore[assignment]


class StripeBillingGateway:
    """Gateway interface for Stripe billing operations.

    Enables real-time customer registration, subscription generation,
    usage reporting, webhook parsing, and F2 security quarantine.
    """

    def __init__(self, config: StripeBillingConfig | None = None):
        self.config = config or load_stripe_billing_config()
        self.is_mock = not self.config.secret_key or self.config.secret_key.startswith("sk_test_mock")

        if not self.is_mock and stripe is not None:
            stripe.api_key = self.config.secret_key
        else:
            if stripe is None:
                logger.info("[BILLING] stripe package not installed. Running in mock mode.")
            else:
                logger.info("[BILLING] Running in mock mode due to mock/missing Stripe credentials.")

    def create_customer(self, tenant_id: str, email: str) -> str:
        """Create a customer in Stripe or mock.

        Returns:
            Stripe customer ID string.
        """
        if self.is_mock or stripe is None:
            mock_cus = f"cus_mock_{tenant_id}"
            logger.info("[BILLING][MOCK] Created customer %s for email %s", mock_cus, email)
            return mock_cus

        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={"tenant_id": tenant_id},
            )
            return customer.id
        except Exception as e:
            logger.error("Failed to create Stripe customer for %s: %s", tenant_id, e)
            raise

    def create_subscription(self, customer_id: str, plan: str) -> str:
        """Create a subscription to a specified plan in Stripe or mock.

        Returns:
            Stripe subscription ID.
        """
        price_id = self.config.price_table.get(plan, "")
        if self.is_mock or stripe is None:
            mock_sub = f"sub_mock_{customer_id[:8]}"
            logger.info("[BILLING][MOCK] Subscribed customer %s to plan %s (price=%s)", customer_id, plan, price_id)
            return mock_sub

        if not price_id:
            raise ValueError(f"Stripe Price ID not configured for plan '{plan}'")

        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
            )
            return subscription.id
        except Exception as e:
            logger.error("Failed to create Stripe subscription for customer %s on plan %s: %s", customer_id, plan, e)
            raise

    def report_usage(self, subscription_item_id: str, quantity: int) -> None:
        """Report metered usage quantity to Stripe.

        Args:
            subscription_item_id: Stripe subscription item ID.
            quantity: Increment quantity for usage.
        """
        if self.is_mock or stripe is None:
            logger.info("[BILLING][MOCK] Reported usage: subscription_item=%s quantity=%d", subscription_item_id, quantity)
            return

        try:
            stripe.SubscriptionItem.create_usage_record(
                subscription_item_id,
                quantity=quantity,
                timestamp="now",
                action="increment",
            )
        except Exception as e:
            logger.error("Failed to report usage for Stripe subscription item %s: %s", subscription_item_id, e)
            raise

    def handle_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        """Validate and parse incoming Stripe webhook payloads.

        Args:
            payload: Raw bytes of the HTTP request body.
            signature: Stripe-Signature header value.

        Returns:
            Parsed webhook event object dictionary.
        """
        if self.is_mock or stripe is None:
            # Simple mock payload bypass (useful for E2E testing)
            import json
            try:
                data = json.loads(payload.decode("utf-8"))
                logger.info("[BILLING][MOCK] Parsed mock webhook event type %s", data.get("type"))
                return data
            except Exception as e:
                logger.error("Failed to decode mock webhook payload: %s", e)
                return {"type": "unknown", "data": {}}

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.config.webhook_secret
            )
            return event
        except Exception as e:
            logger.error("Webhook verification failed: %s", e)
            raise ValueError(f"Invalid webhook signature: {e}") from e

    def quarantine_revenue(self, event: BillingEvent) -> None:
        """Applies premium Failure tax logic: F2 (adversarial exploits) triggers revenue quarantine.

        Args:
            event: The metered BillingEvent to evaluate.
        """
        if event.failure_type == FailureType.F2:
            event.revenue_quarantined = True
            logger.critical(
                "🚨 [SECURITY QUARANTINE] Revenue Quarantine Triggered for event %s. "
                "Agent: %s, Cause: Induced/Adversarial Failure (F2). SSU: %.2f. Cost: $%.4f. "
                "Escalating to immediate Observability Kernel review.",
                event.event_id,
                event.agent_id,
                event.ssu_units,
                event.cost_usd,
            )
        else:
            logger.info("[BILLING] Event %s processed without security quarantine.", event.event_id)
