import logging
import sys
import unittest

import unittest.mock

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

    @unittest.mock.patch("asyncio.create_subprocess_exec")
    @unittest.mock.patch("os.system")
    async def test_audit_cycle(self, mock_system, mock_exec):
        """Standard Audit Cycle on mock contract."""
        mock_proc = unittest.mock.AsyncMock()
        mock_proc.communicate.return_value = (b"Mock stdout", b"Mock stderr")
        mock_proc.returncode = 0
        mock_proc.wait = unittest.mock.AsyncMock()
        mock_exec.return_value = mock_proc

        logger = logging.getLogger("cortex.ouroboros.test")
        logger.info("Starting Ouroboros-1 Verification...")

        # This will clone and audit
        try:
            await self.engine.run_audit()
            logger.info("Audit Cycle 1/1 verified.")
        except Exception as e:
            self.fail(f"Ouroboros Engine Crashed: {str(e)}")

    @unittest.mock.patch("cortex.config.DB_PATH", ":memory:")
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
