import os
import sys
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
        
        # Ensure torch and sentence_transformers are NOT already in sys.modules
        # (This assumes the test runner hasn't already loaded them)
        self.assertNotIn('torch', sys.modules, "torch should not be loaded before engine init")
        self.assertNotIn('sentence_transformers', sys.modules, "sentence_transformers should not be loaded before engine init")

        CortexEngine()
        
        self.assertNotIn('torch', sys.modules, "torch should not be loaded after engine init")
        self.assertNotIn('sentence_transformers', sys.modules, "sentence_transformers should not be loaded after engine init")

    def test_store_no_torch(self):
        """Verify that basic store operation does not load torch."""
        import asyncio

        from cortex.engine import CortexEngine

        engine = CortexEngine()
        
        async def run_store():
            await engine.store("test_project", "dependency isolation test fact", source="test")

        asyncio.run(run_store())

        self.assertNotIn('torch', sys.modules, "torch should not be loaded after store operation")
        self.assertNotIn('sentence_transformers', sys.modules, "sentence_transformers should not be loaded after store operation")

if __name__ == "__main__":
    unittest.main()
