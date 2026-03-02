from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cortex.engine.apotheosis import ApotheosisEngine
from cortex.engine.endocrine import ENDOCRINE, HormoneType


@pytest.mark.asyncio
async def test_targeted_reflex_on_rejection_signal():
    """Verify that ApotheosisEngine triggers a targeted Keter response on rejection signals."""
    workspace = Path("/tmp/mock_workspace")
    cortex_mock = MagicMock()

    # Mock database and signal bus
    with (
        patch("sqlite3.connect"),
        patch("cortex.signals.bus.SignalBus.peek") as mock_peek,
        patch("cortex.engine.keter.KeterEngine.ignite") as mock_ignite,
    ):
        # 1. Setup Signal
        mock_signal = MagicMock()
        mock_signal.payload = {"file": "problematic_file.py", "reason": "AST failure"}
        mock_peek.return_value = [mock_signal]

        engine = ApotheosisEngine(workspace, cortex_engine=cortex_mock)
        # Mock _cortex behavior for reflex
        engine._cortex._db_path = "/tmp/mock.db"

        # 2. Trigger Reflex
        from cortex.engine.reflex import trigger_autonomic_reflex
        reflex_tasks = set()
        await trigger_autonomic_reflex(workspace, engine._cortex, reflex_tasks)

        # 3. Verify target Keter ignition
        mock_ignite.assert_called_once()
        args, kwargs = mock_ignite.call_args
        assert "problematic_file.py" in args[0]
        assert "AST failure" in args[0]


@pytest.mark.asyncio
async def test_adrenal_override_bypasses_dampening():
    """Verify that high adrenaline bypasses cognitive dampening."""
    engine = ApotheosisEngine(Path("/tmp"))
    engine._cognitive_weight = 0.1  # Very low, should be dampened
    engine._inertia_threshold = 0.7

    # Normally dampened
    assert engine._apply_cognitive_dampening() is False

    # Pulse adrenaline to 1.0 (Omega State)
    ENDOCRINE.pulse(HormoneType.ADRENALINE, 1.0)

    # Should now bypass
    assert engine._apply_cognitive_dampening() is True

    # Reset for other tests if necessary
    ENDOCRINE.pulse(HormoneType.ADRENALINE, -1.0)


if __name__ == "__main__":
    pytest.main([__file__])
