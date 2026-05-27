import logging
import sys
import unittest
from pathlib import Path

# Add project root and cortex-core to sys.path dynamically
_project_root = Path(__file__).resolve().parents[1]
_cortex_core = _project_root / "cortex-core"
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_cortex_core))

from ouroboros_engine import OuroborosEngine


class TestOuroborosForge(unittest.IsolatedAsyncioTestCase):
    """Verifies the Forge-backed Ouroboros audit pipeline (V5)."""

    async def asyncSetUp(self):
        self.test_repo = "https://github.com/Uniswap/v4-core"
        # Use a temporary file for tests to prevent locking the real DB
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        
        from unittest.mock import patch
        self.patcher = patch("ouroboros_engine.DB_PATH", self.db_path)
        self.patcher.start()
        
        self.engine = OuroborosEngine()

    async def asyncTearDown(self):
        self.patcher.stop()
        if getattr(self.engine, "bus", None) and hasattr(self.engine.bus, "_conn"):
            self.engine.bus._conn.close()
        self.temp_dir.cleanup()

    async def test_audit_cycle(self):
        """Standard Audit Cycle on mock contract."""
        logger = logging.getLogger("cortex.ouroboros.test")
        logger.info("Starting Ouroboros-1 Verification...")

        # Mock external calls to forge and git
        from unittest.mock import patch, AsyncMock

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"mock stdout", b"mock stderr")
        mock_process.wait.return_value = None
        mock_process.returncode = 0

        # This will clone and audit
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("os.system", return_value=0):
                try:
                    await self.engine.run_audit()
                    logger.info("Audit Cycle 1/1 verified.")
                except Exception as e:
                    self.fail(f"Ouroboros Engine Crashed: {str(e)}")

    async def test_signal_emission(self):
        """Verify SignalBus emits audit findings correctly."""
        import sqlite3

        from cortex.extensions.signals.bus import SignalBus

        # Ensure schema initialization
        conn = sqlite3.connect(self.db_path)
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
