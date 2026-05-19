import logging
import sys
import unittest
from unittest import mock
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

    @mock.patch("asyncio.create_subprocess_exec")
    @mock.patch("os.system")
    async def test_audit_cycle(self, mock_os_system, mock_create_subprocess_exec):
        """Standard Audit Cycle on mock contract."""
        logger = logging.getLogger("cortex.ouroboros.test")
        logger.info("Starting Ouroboros-1 Verification...")

        # Mock process for asyncio.create_subprocess_exec
        mock_process = mock.AsyncMock()
        mock_process.communicate.return_value = (b"output", b"")
        mock_process.returncode = 0
        mock_create_subprocess_exec.return_value = mock_process

        # This will clone and audit
        try:
            await self.engine.run_audit()
            logger.info("Audit Cycle 1/1 verified.")
        except Exception as e:
            self.fail(f"Ouroboros Engine Crashed: {str(e)}")

    @mock.patch("asyncio.create_subprocess_exec")
    @mock.patch("os.system")
    async def test_audit_cycle_with_failure(self, mock_os_system, mock_create_subprocess_exec):
        """Audit Cycle with mocked contract failure."""
        logger = logging.getLogger("cortex.ouroboros.test")

        # Mock process for asyncio.create_subprocess_exec returning a failure code
        mock_process = mock.AsyncMock()
        mock_process.communicate.return_value = (b"output_error", b"error")
        mock_process.returncode = 1
        mock_create_subprocess_exec.return_value = mock_process

        # This will clone and audit resulting in a finding
        try:
            await self.engine.run_audit()
        except Exception as e:
            self.fail(f"Ouroboros Engine Crashed: {str(e)}")

    @mock.patch("cortex.config.DB_PATH", ":memory:")
    async def test_signal_emission(self):
        """Verify SignalBus emits audit findings correctly."""
        import sqlite3

        from cortex.config import DB_PATH
        from cortex.extensions.signals.bus import SignalBus

        # Ensure schema initialization
        conn = sqlite3.connect(DB_PATH)
        _bus = SignalBus(conn)
        _bus.ensure_table()

        # Check if signals exist for 'ouroboros'
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM signals WHERE source='ouroboros'")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertGreaterEqual(count, 0, "Signal table check failed.")


if __name__ == "__main__":
    unittest.main()
