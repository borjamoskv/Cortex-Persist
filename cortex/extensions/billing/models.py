# [C5-REAL] Exergy-Maximized
"""CORTEX Billing Core - Data Models.

Defines the transactional and causal billing structures, as well as failure taxonomy.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class FailureType(Enum):
    """Failure classification for the CORTEX premium failure tax system."""

    F1 = "F1"  # Stochastic/natural failure (baseline)
    F2 = "F2"  # Induced/adversarial failure (exploit attempt)
    F3 = "F3"  # Synthetic failure (simulation-as-product)


@dataclass
class BillingEvent:
    """A metered billing event representing compute cost and causal footprint.

    Attributes:
        event_id: Unique event identifier (UUID hex).
        agent_id: The ID of the agent executing the work.
        ssu_units: Standard Swarm Units computed for resource consumption.
        cost_usd: Total computed cost in USD.
        causal_link: Cryptographic hash or event ID of the causal parent/trigger.
        reproducibility_score: Deterministic reproducibility index [0.0 - 1.0].
        exploitability_index: Security vulnerability score [0.0 - 1.0].
        failure_type: Type of failure encountered (if any).
        revenue_quarantined: Whether the associated billing amount is quarantined (e.g. on F2).
        timestamp: Epoch timestamp (seconds).
        meta: Additional metadata dictionary.
    """

    agent_id: str
    ssu_units: float
    cost_usd: float
    causal_link: str
    reproducibility_score: float = 1.0
    exploitability_index: float = 0.0
    failure_type: FailureType | None = None
    revenue_quarantined: bool = False
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: int = field(default_factory=lambda: int(time.time()))
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for storage or APIs."""
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "ssu_units": self.ssu_units,
            "cost_usd": self.cost_usd,
            "causal_link": self.causal_link,
            "reproducibility_score": self.reproducibility_score,
            "exploitability_index": self.exploitability_index,
            "failure_type": self.failure_type.value if self.failure_type else None,
            "revenue_quarantined": self.revenue_quarantined,
            "timestamp": self.timestamp,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BillingEvent:
        """De-serialize from dictionary."""
        ft = data.get("failure_type")
        failure_type = FailureType(ft) if ft else None
        return cls(
            agent_id=data["agent_id"],
            ssu_units=data["ssu_units"],
            cost_usd=data["cost_usd"],
            causal_link=data["causal_link"],
            reproducibility_score=data.get("reproducibility_score", 1.0),
            exploitability_index=data.get("exploitability_index", 0.0),
            failure_type=failure_type,
            revenue_quarantined=data.get("revenue_quarantined", False),
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            meta=data.get("meta") or {},
        )


@dataclass(frozen=True)
class StripeInvoice:
    """Read-only details of a Stripe invoice transaction."""

    invoice_id: str
    customer_id: str
    subscription_id: str | None
    amount_due: int  # in cents
    amount_paid: int  # in cents
    currency: str
    status: str
    hosted_invoice_url: str | None = None
    created_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
