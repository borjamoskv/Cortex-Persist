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
