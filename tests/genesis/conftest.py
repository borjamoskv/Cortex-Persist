"""conftest.py for tests/genesis/

Autouse fixture: stubs GenesisEngine._persist_to_cortex across the entire suite.

Rationale:
    _persist_to_cortex instantiates a live CortexEngine and enforces exergy
    thresholds. Genesis tests validate filesystem creation and template logic,
    not CORTEX ledger persistence — which has its own test suite (test_store_mixin,
    test_exergy, etc). Any live CortexEngine call here is an uncontrolled side
    effect that breaks test isolation under ThermodynamicWasteError.
"""
from __future__ import annotations

import pytest

from cortex.extensions.genesis.engine import GenesisEngine


@pytest.fixture(autouse=True)
def stub_persist_to_cortex(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suppress CORTEX ledger persistence for all genesis engine tests."""
    monkeypatch.setattr(GenesisEngine, "_persist_to_cortex", lambda self, result: None)
