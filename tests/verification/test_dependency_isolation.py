# [C5-REAL] Exergy-Maximized
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
        self.old_no_embed = os.environ.get("CORTEX_NO_EMBED")
        self.old_no_taint = os.environ.get("CORTEX_NO_TAINT_ENFORCE")
        # Force auto_embed off for core tests
        os.environ["CORTEX_NO_EMBED"] = "true"
        os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"

    def tearDown(self):
        if self.old_no_embed is not None:
            os.environ["CORTEX_NO_EMBED"] = self.old_no_embed
        else:
            os.environ.pop("CORTEX_NO_EMBED", None)

        if self.old_no_taint is not None:
            os.environ["CORTEX_NO_TAINT_ENFORCE"] = self.old_no_taint
        else:
            os.environ.pop("CORTEX_NO_TAINT_ENFORCE", None)

    def test_engine_init_no_torch(self):
        """Verify that initializing CortexEngine does not load torch."""
        from babylon60.engine import CortexEngine

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
        from babylon60.engine import CortexEngine

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
