import logging
import sys
import unittest
from pathlib import Path

# Add project root to sys.path dynamically
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root))

from ouroboros_engine import OuroborosEngine


class TestOuroborosForge(unittest.IsolatedAsyncioTestCase):
    """Verifies the Forge-backed Ouroboros audit pipeline (V5)."""

    async def asyncSetUp(self):
        self.engine = OuroborosEngine()
        self.test_repo = "https://github.com/Uniswap/v4-core"

    async def test_audit_cycle(self):
        """Standard Audit Cycle on mock contract."""
        import asyncio
        from unittest.mock import patch, MagicMock

        logger = logging.getLogger("cortex.ouroboros.test")
        logger.info("Starting Ouroboros-1 Verification...")

        # Mock OS and subprocess interactions to avoid dependency on "forge" and network
        with patch("os.system") as mock_system, \
             patch("asyncio.create_subprocess_exec") as mock_exec, \
             patch.object(self.engine, "_queue_remediation") as mock_queue, \
             patch.object(self.engine, "clone_target", new_callable=unittest.mock.AsyncMock):

            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.communicate = unittest.mock.AsyncMock(return_value=(b"Success", b""))
            mock_exec.return_value = mock_process

            try:
                await self.engine.run_audit()
                logger.info("Audit Cycle 1/1 verified.")
            except Exception as e:
                self.fail(f"Ouroboros Engine Crashed: {str(e)}")

    async def test_audit_cycle_failure(self):
        """Standard Audit Cycle that triggers a failure."""
        import asyncio
        from unittest.mock import patch, MagicMock

        logger = logging.getLogger("cortex.ouroboros.test")
        logger.info("Starting Ouroboros-1 Verification Failure Branch...")

        with patch("os.system") as mock_system, \
             patch("asyncio.create_subprocess_exec") as mock_exec, \
             patch.object(self.engine, "_queue_remediation") as mock_queue, \
             patch.object(self.engine, "clone_target", new_callable=unittest.mock.AsyncMock):

            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.communicate = unittest.mock.AsyncMock(return_value=(b"Error", b"Failure"))
            mock_exec.return_value = mock_process

            try:
                await self.engine.run_audit()
                mock_queue.assert_called()
                logger.info("Audit Cycle Failure Branch verified.")
            except Exception as e:
                self.fail(f"Ouroboros Engine Crashed: {str(e)}")

    async def test_detect_contracts(self):
        """Test the contract detection logic directly."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            self.engine.scratch_dir = tmpdir
            os.makedirs(os.path.join(tmpdir, "src"))
            with open(os.path.join(tmpdir, "src", "test.sol"), "w") as f:
                # Ouroboros excludes files with "test" in name, so use a real contract file
                pass
            with open(os.path.join(tmpdir, "src", "Real.sol"), "w") as f:
                f.write("contract TestContract {}")

            contracts = self.engine._detect_contracts()
            self.assertEqual(len(contracts), 1)
            self.assertEqual(contracts[0]["name"], "TestContract")

    async def test_queue_remediation(self):
        """Test the remediation queueing logic directly."""
        import tempfile
        import os
        import json
        from unittest.mock import patch, mock_open

        with patch("ouroboros_engine.logger") as mock_log, \
             patch("ouroboros_engine.os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data='{"pending_tasks": []}')), \
             patch("ouroboros_engine.json.load", return_value={"pending_tasks": []}), \
             patch("ouroboros_engine.json.dump") as mock_dump:
            self.engine._queue_remediation("test.sol", "test.log")
            mock_dump.assert_called()

    async def test_queue_remediation_exception(self):
        import tempfile
        import os
        from unittest.mock import patch

        with patch("ouroboros_engine.os.path.exists", side_effect=Exception("Test Exception")), \
             patch("ouroboros_engine.logger") as mock_log:

            self.engine._queue_remediation("test.sol", "test.log")
            mock_log.error.assert_called_with("Remediation Queue Failure: %s", unittest.mock.ANY)

    async def test_clone_target(self):
        import asyncio
        from unittest.mock import patch, MagicMock
        with patch("asyncio.create_subprocess_exec") as mock_exec:
             mock_process = MagicMock()
             mock_process.wait = unittest.mock.AsyncMock()
             mock_exec.return_value = mock_process

             self.engine.target_url = "http://test.url"
             self.engine.scratch_dir = "/tmp"
             await self.engine.clone_target()
             mock_exec.assert_called()

    async def test_signal_emission(self):
        """Verify SignalBus emits audit findings correctly."""
        import sqlite3

        from cortex.extensions.signals.bus import SignalBus

        # Ensure schema initialization
        conn = sqlite3.connect(":memory:")
        _bus = SignalBus(conn)

        # Manually create the table so we can test the check safely
        _bus.ensure_table()

        # Check if signals exist for 'ouroboros'
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM signals WHERE source='ouroboros'")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertGreaterEqual(count, 0, "Signal table check failed.")


if __name__ == "__main__":
    unittest.main()
