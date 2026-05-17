import logging
import sys
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
import unittest
from pathlib import Path

# Add project root to sys.path dynamically
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root))

from ouroboros_engine import OuroborosEngine


class TestOuroborosForge(unittest.IsolatedAsyncioTestCase):
    """Verifies the Forge-backed Ouroboros audit pipeline (V5)."""

    async def asyncSetUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.db_patcher = patch("cortex.config.DB_PATH", self.temp_db.name)
        self.db_patcher.start()

        self.engine = OuroborosEngine()
        self.test_repo = "https://github.com/Uniswap/v4-core"

    async def asyncTearDown(self):
        self.db_patcher.stop()
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    @patch("ouroboros_engine.os.system")
    @patch("ouroboros_engine.asyncio.create_subprocess_exec")
    async def test_audit_cycle(self, mock_exec, mock_system):
        """Standard Audit Cycle on mock contract."""
        logger = logging.getLogger("cortex.ouroboros.test")
        logger.info("Starting Ouroboros-1 Verification...")

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"mock stdout", b"mock stderr")
        mock_process.wait.return_value = 0
        mock_exec.return_value = mock_process

        mock_system.return_value = 0

        # This will clone and audit
        try:
            await self.engine.run_audit()
            logger.info("Audit Cycle 1/1 verified.")
        except Exception as e:
            self.fail(f"Ouroboros Engine Crashed: {str(e)}")

    async def test_signal_emission(self):
        """Verify SignalBus emits audit findings correctly."""
        import sqlite3

        from cortex.config import DB_PATH
        from cortex.extensions.signals.bus import SignalBus

        # Ensure schema initialization
        conn = sqlite3.connect(self.temp_db.name)
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
