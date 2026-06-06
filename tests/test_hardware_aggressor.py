# [C5-REAL] Exergy-Maximized
import asyncio
import pytest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cortex-core")))
from k0_swarm_node import HardwareAggressor


@pytest.mark.asyncio
async def test_hardware_aggressor_c4_sim():
    """
    Validate that HardwareAggressor correctly falls back to C4-SIM mode
    when akash binary is not present, incrementing active_nodes.
    """
    with patch("shutil.which", return_value=None):
        mock_ledger = MagicMock()
        aggressor = HardwareAggressor(ledger=mock_ledger)

        # Verify initial state (starts at 10000 nodes)
        assert aggressor.active_nodes == 10000

        # Execute deployment
        result = await aggressor._deploy_to_akash()

        # Verify it still increments physical node count in sim
        assert aggressor.active_nodes == 10001


@pytest.mark.asyncio
async def test_hardware_aggressor_c5_real(monkeypatch):
    """
    Validate that HardwareAggressor constructs the correct CLI command
    when akash binary is present.
    """
    with patch("shutil.which", return_value="/usr/local/bin/akash"):
        monkeypatch.setenv("AKASH_WALLET_ADDRESS", "akash1mockwallet")

        mock_ledger = MagicMock()
        aggressor = HardwareAggressor(ledger=mock_ledger)

        # Mock create_subprocess_exec
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"mock_tx_hash_123", b"")
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await aggressor._deploy_to_akash()

            # Verify subprocess was called with the right arguments
            mock_exec.assert_called_once()
            args = mock_exec.call_args[0]
            # Since akash is present, it will run akash command instead of /usr/bin/env
            assert args[0] == "/usr/local/bin/akash"
            assert "tx" in args
            assert "deployment" in args
            assert "akash1mockwallet" in args

            assert aggressor.active_nodes == 10001
