# [C5-REAL] Exergy-Maximized
import pytest
from babylon60.runtime.state import RuntimeState
from babylon60.runtime.replay.ledger import EventLedger
from babylon60.runtime.replay.engine import ReplayEngine, DivergenceException


def test_deterministic_replay():
    # Setup Ledger
    ledger = EventLedger()
    ledger.append({"action_type": "MEMORY_WRITE", "payload": {"tick": 1, "k1": "v1"}})
    ledger.append({"action_type": "MEMORY_WRITE", "payload": {"tick": 2, "k2": "v2"}})

    events = ledger.export()

    # Run Engine once to get the true hashes
    engine = ReplayEngine(RuntimeState)
    snapshots = engine.run(events)

    assert len(snapshots) == 3  # Bootstrap + 2 events

    # Map version to true hash
    expected_hashes = {snap["version"]: snap["state_hash"] for snap in snapshots}

    # Replay with correct hashes
    engine.run(events, expected_hashes=expected_hashes)  # Should not raise

    # Replay with incorrect hash
    bad_hashes = expected_hashes.copy()
    bad_hashes[2] = "invalid_hash_value"

    with pytest.raises(DivergenceException) as excinfo:
        engine.run(events, expected_hashes=bad_hashes)

    assert "DIVERGENCE DETECTED" in str(excinfo.value)
    assert "invalid_hash_value" in str(excinfo.value)
