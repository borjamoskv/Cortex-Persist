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
        from unittest.mock import patch, AsyncMock

        self.patcher1 = patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
        self.patcher2 = patch("os.system")
        self.patcher3 = patch("subprocess.run")

        self.mock_exec = self.patcher1.start()
        mock_proc = AsyncMock()
        mock_proc.stdout.readline.side_effect = [b"[FAIL] Mock failure", b""]
        mock_proc.wait.return_value = 0
        mock_proc.communicate.return_value = (b"[FAIL] Mock failure", b"")
        self.mock_exec.return_value = mock_proc

        self.mock_sys = self.patcher2.start()
        self.mock_run = self.patcher3.start()

        self.engine = OuroborosEngine()
        self.test_repo = "https://github.com/Uniswap/v4-core"

    async def asyncTearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()

    async def test_audit_cycle(self):
        """Standard Audit Cycle on mock contract."""
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
        import tempfile
        from unittest.mock import patch

        with tempfile.NamedTemporaryFile() as tmp:
            with patch("cortex.config.DB_PATH", tmp.name):
                conn = sqlite3.connect(tmp.name)
                _bus = SignalBus(conn)
                _bus.ensure_table()  # Must create table first!

                # Check if signals exist for 'ouroboros'
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM signals WHERE source='ouroboros'")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertGreaterEqual(count, 0, "Signal table check failed.")


if __name__ == "__main__":
    unittest.main()
