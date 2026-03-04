"""Tests for TOM and OLIVER signal convergence protocol."""

import aiosqlite
import pytest

from cortex.sap.agents.oliver import OliverAgent
from cortex.sap.agents.tom import TomAgent
from cortex.signals.bus import AsyncSignalBus


@pytest.mark.asyncio
async def test_tom_oliver_convergence():
    # Setup temporary in-memory-like DB for testing
    async with aiosqlite.connect(":memory:") as conn:
        bus = AsyncSignalBus(conn)
        await bus.ensure_table()

        tom = TomAgent(conn)
        oliver = OliverAgent(conn)

        # Scenario: Some transactions including one massive outlier and a SOD violation
        txs = [
            {"id": "001", "amount": 500, "created_by": "USER_A", "approved_by": "USER_B"},
            {"id": "002", "amount": 12_500_000, "created_by": "USER_C", "approved_by": "USER_D"},
            {"id": "003", "amount": 800, "created_by": "USER_E", "approved_by": "USER_E"},
        ]

        # 1. TOM Scans
        findings = await tom.audit_transactions(txs)
        assert findings == 2, "TOM should have found 2 anomalies"

        # Verify signals in bus
        history = await bus.history(event_type="sap:audit:finding", source="tom-tracker")
        assert len(history) == 2, "TOM should have emitted 2 finding signals"

        # 2. OLIVER Polls and Reacts
        effects = await oliver.listen_and_react()

        # Oliver should process both and emit effects
        # Tx2 is 12.5M (High + 10M = 0.3 + 0.4 = 0.7 score -> FREEZE_ACCOUNT)
        # Tx3 is SOD (Critical + <1M = 0.5 + 0.0 = 0.5 score -> NOTIFY_BOARD)
        # Therefore, Oliver should emit 2 effects
        assert effects == 2, "OLIVER should have emitted 2 effects based on material findings"

        # Verify effect signals in bus
        effect_history = await bus.history(event_type="sap:audit:effect", source="oliver-hammer")
        assert len(effect_history) == 2, "OLIVER should have emitted 2 effect signals"

        actions = {e.payload.get("action") for e in effect_history}
        assert "FREEZE_ACCOUNT" in actions
        assert "NOTIFY_BOARD" in actions


@pytest.mark.asyncio
async def test_metabolic_loop_prevention():
    """Verify TOM ignores OLIVER's output signals to prevent infinite loops (Ω₃)."""
    async with aiosqlite.connect(":memory:") as conn:
        bus = AsyncSignalBus(conn)
        await bus.ensure_table()
        tom = TomAgent(conn)

        # Oliver's effect signal, which might look like a transaction but it's internal
        oliver_signal_as_tx = {
            "id": "SIGNAL_999",
            "amount": 50_000_000,  # Massive amount, TOM would find it normally
            "agent": "OLIVER",
            "source": "agent:oliver",
            "action": "BLOCK_USER",
        }

        # TOM should ignore it
        findings = await tom.audit_transactions([oliver_signal_as_tx])
        assert findings == 0, "TOM must ignore internal agent signals to prevent loops"
