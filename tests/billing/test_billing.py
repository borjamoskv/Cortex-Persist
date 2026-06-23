# [C5-REAL] Exergy-Maximized
"""CORTEX Billing Core - Comprehensive Test Suite.

Verifies model serialization, Stripe mock integration, causal metering cost multipliers,
economic exergy math, security revenue quarantine, and SQLite persistence.
"""

from __future__ import annotations

import os
import tempfile
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "lab"))
from stripe_config import StripeBillingConfig
from babylon60.extensions.billing.models import BillingEvent, FailureType, StripeInvoice
from babylon60.extensions.billing.gateway import StripeBillingGateway
from babylon60.extensions.billing.metering import CausalMetering


@pytest.fixture
def tmp_db():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


# ─── Model Tests ─────────────────────────────────────────────────────

def test_billing_event_serialization():
    """BillingEvent should serialize and deserialize correctly."""
    event = BillingEvent(
        agent_id="test-agent",
        ssu_units=12.5,
        cost_usd=0.125,
        causal_link="hash123",
        reproducibility_score=0.95,
        exploitability_index=0.1,
        failure_type=FailureType.F1,
        meta={"execution_id": "exec_456"},
    )

    data = event.to_dict()
    assert data["agent_id"] == "test-agent"
    assert data["ssu_units"] == 12.5
    assert data["cost_usd"] == 0.125
    assert data["failure_type"] == "F1"
    assert data["meta"] == {"execution_id": "exec_456"}
    assert data["revenue_quarantined"] is False

    restored = BillingEvent.from_dict(data)
    assert restored.event_id == event.event_id
    assert restored.agent_id == "test-agent"
    assert restored.ssu_units == 12.5
    assert restored.cost_usd == 0.125
    assert restored.failure_type == FailureType.F1
    assert restored.meta == {"execution_id": "exec_456"}


def test_stripe_invoice_serialization():
    """StripeInvoice should convert to dict cleanly."""
    invoice = StripeInvoice(
        invoice_id="in_123",
        customer_id="cus_abc",
        subscription_id="sub_xyz",
        amount_due=5000,
        amount_paid=5000,
        currency="usd",
        status="paid",
    )
    data = invoice.to_dict()
    assert data["invoice_id"] == "in_123"
    assert data["amount_due"] == 5000
    assert data["status"] == "paid"


# ─── Gateway Tests ───────────────────────────────────────────────────

def test_gateway_mock_creation():
    """StripeBillingGateway should initialize and handle mock mode."""
    config = StripeBillingConfig(
        secret_key="sk_test_mock_123",
        webhook_secret="whsec_mock_456",
        price_table={"pro": "price_pro_123"},
    )
    gateway = StripeBillingGateway(config)
    assert gateway.is_mock is True

    # Check mock operations return structured strings
    cus = gateway.create_customer("tenant-1", "test@babylon60.com")
    assert cus == "cus_mock_tenant-1"

    sub = gateway.create_subscription(cus, "pro")
    assert sub == "sub_mock_cus_mock"

    # Webhook mock parser should load json payload
    raw_payload = b'{"type": "invoice.paid", "data": {"object": {"id": "in_1"}}}'
    event = gateway.handle_webhook(raw_payload, "sig")
    assert event["type"] == "invoice.paid"
    assert event["data"]["object"]["id"] == "in_1"


# ─── Metering Tests ──────────────────────────────────────────────────

def test_cost_calculation():
    """CausalMetering should calculate costs based on SSU and failure multipliers."""
    metering = CausalMetering(db_path=":memory:")

    # 1. Success case (no failure -> multiplier 1.0)
    # SSU = (10s * 1.5) + (5000 * 0.0001) + (3 * 2.0) = 15.0 + 0.5 + 6.0 = 21.5 SSU
    # Cost = 21.5 SSU * 0.01 * 1.0 = $0.215
    ssu, cost = metering.calculate_cost(duration=10.0, tokens_used=5000, search_depth=3)
    assert ssu == 21.5
    assert cost == 0.215

    # 2. Stochastic failure (F1 -> multiplier 0.5)
    # Cost = 21.5 SSU * 0.01 * 0.5 = $0.1075
    ssu, cost = metering.calculate_cost(duration=10.0, tokens_used=5000, search_depth=3, failure_type=FailureType.F1)
    assert ssu == 21.5
    assert cost == 0.1075

    # 3. Induced failure (F2 -> multiplier 2.0)
    # Cost = 21.5 SSU * 0.01 * 2.0 = $0.43
    ssu, cost = metering.calculate_cost(duration=10.0, tokens_used=5000, search_depth=3, failure_type=FailureType.F2)
    assert ssu == 21.5
    assert cost == 0.43

    # 4. Synthetic failure (F3 -> multiplier 1.0)
    # Cost = 21.5 SSU * 0.01 * 1.0 = $0.215
    ssu, cost = metering.calculate_cost(duration=10.0, tokens_used=5000, search_depth=3, failure_type=FailureType.F3)
    assert ssu == 21.5
    assert cost == 0.215


def test_exergy_evaluation():
    """Exergy evaluation math should compute accurately."""
    metering = CausalMetering(db_path=":memory:")
    # E_net = 1000 - (0.5 * 100) + (0.2 * 50) = 1000 - 50 + 10 = 960.0
    e_net = metering.evaluate_exergy(monthly_income=1000.0, entropy=100.0, novelty=50.0)
    assert e_net == 960.0


# ─── Database Persistence & Quarantine Tests ───────────────────────

def test_record_and_quarantine_flow(tmp_db):
    """CausalMetering should save records and quarantine F2 events."""
    config = StripeBillingConfig(secret_key="sk_test_mock_123")
    gateway = StripeBillingGateway(config)
    metering = CausalMetering(db_path=tmp_db, gateway=gateway)

    # 1. Standard billing event (F1)
    ev1 = BillingEvent(
        agent_id="agent-alice",
        ssu_units=10.0,
        cost_usd=0.10,
        causal_link="link1",
        failure_type=FailureType.F1,
    )
    metering.record_billing_event(ev1)
    assert ev1.revenue_quarantined is False

    # 2. Induced failure event (F2) -> should trigger quarantine flag
    ev2 = BillingEvent(
        agent_id="agent-bob",
        ssu_units=20.0,
        cost_usd=0.40,
        causal_link="link2",
        failure_type=FailureType.F2,
    )
    metering.record_billing_event(ev2)
    assert ev2.revenue_quarantined is True

    # Retrieve from DB and verify
    events = metering.get_billing_events()
    assert len(events) == 2

    # Bob's event (F2) should be quarantined in database
    bob_events = metering.get_billing_events("agent-bob")
    assert len(bob_events) == 1
    assert bob_events[0].revenue_quarantined is True
    assert bob_events[0].ssu_units == 20.0
    assert bob_events[0].cost_usd == 0.40
    assert bob_events[0].failure_type == FailureType.F2

    metering.close()
