import os
os.environ["CORTEX_DB"] = "test_consensus_final.db"
import cortex.config
cortex.config.DB_PATH = "test_consensus_final.db"
from fastapi.testclient import TestClient
import cortex.api
from cortex import api_state
import cortex.auth

cortex.api.DB_PATH = "test_consensus_final.db"
cortex.auth._auth_manager = None
import mock

with mock.patch("cortex.embeddings.LocalEmbedder") as mock_embedder:
    c = TestClient(cortex.api.app)
    raw_key, _ = api_state.auth_manager.create_key("api_agent", tenant_id="test_proj", permissions=["read", "write", "admin"])
    c.headers = {"Authorization": f"Bearer {raw_key}"}
    engine = api_state.engine
    engine.init_db_sync()
    engine.store_sync("test_proj", "Fact A")
    engine.store_sync("test_proj", "Fact B")
    fid_c = engine.store_sync("test_proj", "Fact C")
    c.post(f"/v1/facts/{fid_c}/vote", json={"value": 1})
    resp = c.get("/v1/projects/test_proj/facts")
    print(resp.status_code, resp.json())
