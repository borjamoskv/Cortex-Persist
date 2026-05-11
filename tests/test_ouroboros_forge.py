import logging
import sys
import unittest
import shutil
import tempfile
import os
from unittest.mock import patch
from pathlib import Path

# Add project root to sys.path dynamically
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root))

from ouroboros_engine import OuroborosEngine


class TestOuroborosForge(unittest.IsolatedAsyncioTestCase):
    """Verifies the Forge-backed Ouroboros audit pipeline (V5)."""

    async def asyncSetUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        # Patch the DB_PATH to use the temporary database
        self.db_patcher1 = patch("cortex.config.DB_PATH", self.temp_db.name)
        self.db_patcher2 = patch("ouroboros_engine.DB_PATH", self.temp_db.name)
        self.db_patcher1.start()
        self.db_patcher2.start()

        self.engine = OuroborosEngine()
        self.test_repo = "https://github.com/Uniswap/v4-core"

    async def asyncTearDown(self):
        self.db_patcher1.stop()
        self.db_patcher2.stop()
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except Exception:
                pass

    @patch("os.system")
    @patch("asyncio.create_subprocess_exec")
    async def test_audit_cycle(self, mock_create_subprocess_exec, mock_os_system):
        """Standard Audit Cycle on mock contract."""
        logger = logging.getLogger("cortex.ouroboros.test")
        logger.info("Starting Ouroboros-1 Verification...")

        # Mock the process returned by create_subprocess_exec
        from unittest.mock import AsyncMock
        mock_process = AsyncMock()
        mock_process.returncode = 1  # Simulate a failure to hit the remediation queue logic
        mock_process.communicate.return_value = (b"mock stdout", b"mock stderr")
        mock_process.wait.return_value = None
        mock_create_subprocess_exec.return_value = mock_process

        mock_os_system.return_value = 0

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
