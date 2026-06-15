# [C5-REAL] Exergy-Maximized
"""CORTEX Billing Gateway & Causal Metering Extension."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.billing.models import BillingEvent, FailureType, StripeInvoice
    from cortex.extensions.billing.gateway import StripeBillingGateway
    from cortex.extensions.billing.metering import CausalMetering

__all__ = [
    "BillingEvent",
    "FailureType",
    "StripeInvoice",
    "StripeBillingGateway",
    "CausalMetering",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BillingEvent": ("cortex.extensions.billing.models", "BillingEvent"),
    "FailureType": ("cortex.extensions.billing.models", "FailureType"),
    "StripeInvoice": ("cortex.extensions.billing.models", "StripeInvoice"),
    "StripeBillingGateway": ("cortex.extensions.billing.gateway", "StripeBillingGateway"),
    "CausalMetering": ("cortex.extensions.billing.metering", "CausalMetering"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.extensions.billing' has no attribute {name!r}")
