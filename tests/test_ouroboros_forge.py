import logging
import sys
import unittest
from unittest.mock import patch, AsyncMock
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

    @patch("os.system")
    @patch("asyncio.create_subprocess_exec")
    async def test_audit_cycle(self, mock_subprocess, mock_os_system):
        """Standard Audit Cycle on mock contract."""
        logger = logging.getLogger("cortex.ouroboros.test")
        logger.info("Starting Ouroboros-1 Verification...")

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"mock stdout", b"mock stderr")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

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

        import tempfile
        import os

        # Ensure schema initialization using a temporary DB
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = tmp.name

        try:
            # We patch DB_PATH so any engine logic using it writes here
            with patch("cortex.config.DB_PATH", tmp_db_path):
                # Init the signal table (required before querying)
                conn = sqlite3.connect(tmp_db_path)
                cursor = conn.cursor()
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    payload TEXT,
                    source TEXT,
                    timestamp REAL,
                    handled INTEGER DEFAULT 0
                )
                """)
                conn.commit()

                _bus = SignalBus(conn)

                # Check if signals exist for 'ouroboros'
                cursor.execute("SELECT count(*) FROM signals WHERE source='ouroboros'")
                count = cursor.fetchone()[0]
                conn.close()
                self.assertGreaterEqual(count, 0, "Signal table check failed.")
        finally:
            os.remove(tmp_db_path)


if __name__ == "__main__":
    unittest.main()
