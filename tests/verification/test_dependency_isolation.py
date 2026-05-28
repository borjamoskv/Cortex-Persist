import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestDependencyIsolation(unittest.TestCase):
    def setUp(self):
        # Force auto_embed off for core tests
        os.environ["CORTEX_NO_EMBED"] = "true"
        # Clear any existing cached modules if necessary (risky but for this test we want to be sure)
        # Note: We won't clear sys.modules here as it's a global state,
        # but we will check it.

    def test_engine_init_no_torch(self):
        """Verify that initializing CortexEngine does not load torch."""
        from cortex.engine import CortexEngine

        baseline = {
            name
            for name in sys.modules
            if name == "torch" or name.startswith("sentence_transformers")
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CortexEngine(db_path=str(Path(tmpdir) / "isolation_init.db"), auto_embed=False)
            asyncio.run(engine.close())

        current = {
            name
            for name in sys.modules
            if name == "torch" or name.startswith("sentence_transformers")
        }
        self.assertEqual(current, baseline)

    def test_store_no_torch(self):
        """Verify that basic store operation does not load torch."""
        from cortex.engine import CortexEngine

        baseline = {
            name
            for name in sys.modules
            if name == "torch" or name.startswith("sentence_transformers")
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CortexEngine(
                db_path=str(Path(tmpdir) / "isolation_store.db"), auto_embed=False
            )
            asyncio.run(engine.init_db())

            async def run_store() -> None:
                await engine.store("test_project", "dependency isolation test fact", source="test")

            try:
                asyncio.run(run_store())
            finally:
                asyncio.run(engine.close())

        current = {
            name
            for name in sys.modules
            if name == "torch" or name.startswith("sentence_transformers")
        }
        self.assertEqual(current, baseline)


if __name__ == "__main__":
    unittest.main()
