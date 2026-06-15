# [C5-REAL] Exergy-Maximized Stripe Billing Configuration
from __future__ import annotations

import os
from dataclasses import dataclass, field

from cortex.core import config as cortex_config


@dataclass
class StripeBillingConfig:
    secret_key: str = ""
    webhook_secret: str = ""
    price_table: dict[str, str] = field(default_factory=dict)


def load_stripe_billing_config() -> StripeBillingConfig:
    """Loads Stripe billing configuration from cortex config and environment."""
    cortex_config.reload()

    secret_key = cortex_config.STRIPE_SECRET_KEY or os.environ.get("STRIPE_SECRET_KEY", "")
    webhook_secret = cortex_config.STRIPE_WEBHOOK_SECRET or os.environ.get(
        "STRIPE_WEBHOOK_SECRET", ""
    )
    price_table = cortex_config.STRIPE_PRICE_TABLE

    return StripeBillingConfig(
        secret_key=secret_key,
        webhook_secret=webhook_secret,
        price_table=price_table,
    )


def validate_stripe_billing_config(config: StripeBillingConfig) -> list[str]:
    """Validates the structure and formats of the Stripe configuration."""
    issues: list[str] = []

    if config.secret_key:
        if not (config.secret_key.startswith("sk_") or config.secret_key.startswith("rk_")):
            issues.append("STRIPE_SECRET_KEY must start with 'sk_' or 'rk_'.")

    if config.webhook_secret:
        if not config.webhook_secret.startswith("whsec_"):
            issues.append("STRIPE_WEBHOOK_SECRET must start with 'whsec_'.")

    # Check price table values if configured
    for plan, price_id in config.price_table.items():
        if price_id and not price_id.startswith("price_"):
            issues.append(f"Stripe Price ID for plan '{plan}' must start with 'price_'.")

    return issues
