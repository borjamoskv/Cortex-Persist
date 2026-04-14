import json
from datetime import datetime, timezone

from cortex.extensions.signals.models import Signal
from cortex.routes.events import _serialize_signal
from x100_cortex_server import _signal_payload


def test_routes_events_serializes_dataclass_signal() -> None:
    signal = Signal(
        id=7,
        event_type="ledger_append",
        payload={"yield_amount": 12.5},
        source="test",
        project=None,
        tenant_id="default",
        created_at=datetime(2026, 4, 14, tzinfo=timezone.utc),
        consumed_by=["ui"],
    )

    encoded = _serialize_signal(signal)
    payload = json.loads(encoded)

    assert payload["id"] == 7
    assert payload["event_type"] == "ledger_append"
    assert payload["created_at"].startswith("2026-04-14")
    assert payload["consumed_by"] == ["ui"]


def test_x100_signal_payload_normalizes_datetime() -> None:
    signal = Signal(
        id=9,
        event_type="swarm_task",
        payload={"command": "forge test"},
        source="test",
        project=None,
        tenant_id="default",
        created_at=datetime(2026, 4, 14, tzinfo=timezone.utc),
        consumed_by=[],
    )

    payload = _signal_payload(signal)

    assert payload["id"] == 9
    assert payload["event_type"] == "swarm_task"
    assert payload["created_at"].startswith("2026-04-14")
