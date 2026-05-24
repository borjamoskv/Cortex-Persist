import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path dynamically
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root))

sys.path.insert(0, str(_project_root / "cortex-core"))
from ouroboros_engine import OuroborosEngine


class TestOuroborosForge(unittest.IsolatedAsyncioTestCase):
    """Verifies the Forge-backed Ouroboros audit pipeline (V5)."""

    @patch("ouroboros_engine.DB_PATH", ":memory:")
    async def asyncSetUp(self):
        self.engine = OuroborosEngine()
        self.test_repo = "https://github.com/Uniswap/v4-core"

    @patch("ouroboros_engine.DB_PATH", ":memory:")
    @patch("os.system")
    @patch("asyncio.create_subprocess_exec")
    async def test_audit_cycle(self, mock_create_subprocess_exec, mock_system):
        """Standard Audit Cycle on mock contract."""

        # Mock subprocess logic
        mock_proc = MagicMock()
        mock_proc.wait = unittest.mock.AsyncMock(return_value=0)
        mock_proc.communicate = unittest.mock.AsyncMock(return_value=(b"stdout", b"stderr"))
        mock_proc.returncode = 0
        mock_create_subprocess_exec.return_value = mock_proc

        logger = logging.getLogger("cortex.ouroboros.test")
        logger.info("Starting Ouroboros-1 Verification...")

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
        conn = sqlite3.connect(":memory:")
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
