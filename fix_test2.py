import pytest
import time
from cortex.engine import CortexEngine

def test_mock_embedder(monkeypatch):
    class DummyEmbedder:
        def embed(self, text: str):
            return [0.0] * 768
            
    monkeypatch.setattr("cortex.engine.CortexEngine._get_embedder", lambda self: DummyEmbedder())

    start = time.time()
    engine = CortexEngine()
    engine.init_db_sync()
    engine.store_sync("proj", "test", auto_embed=True)
    engine.close_sync()
    print(f"Time with mock: {time.time() - start:.2f}s")

if __name__ == "__main__":
    pytest.main(["-s", "fix_test2.py"])
