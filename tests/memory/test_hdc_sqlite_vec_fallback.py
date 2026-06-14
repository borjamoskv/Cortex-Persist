import pytest
import sqlite3
import numpy as np
from unittest.mock import patch, MagicMock
from cortex.memory.hdc.store import HDCVectorStoreL2
from cortex.memory.hdc.codec import HDCEncoder
from cortex.memory.hdc.item_memory import ItemMemory
from cortex.memory.models import CortexFactModel

@pytest.fixture
def mock_store(tmp_path):
    item_mem = ItemMemory(dim=128)
    encoder = HDCEncoder(item_mem)
    db_file = tmp_path / "hdc.db"
    return HDCVectorStoreL2(encoder, item_mem, db_path=db_file)

@pytest.mark.asyncio
async def test_hdc_store_sqlite_vec_fallback_operations(mock_store):
    """Verify that HDCVectorStoreL2 correctly handles missing sqlite_vec by falling back without crashing."""

    # Force the class to not use sqlite_vec natively
    mock_store._vec_loaded = False

    # We patch sqlite3.connect to return a mocked connection object that throws OperationalError for vec0 features
    original_connect = sqlite3.connect

    def mocked_connect(*args, **kwargs):
        conn = original_connect(*args, **kwargs)
        original_execute = conn.execute
        original_cursor = conn.cursor

        def mocked_execute(sql, *exec_args, **exec_kwargs):
            if "USING vec0" in sql:
                raise sqlite3.OperationalError("no such module: vec0")
            return original_execute(sql, *exec_args, **exec_kwargs)

        class MockCursor:
            def __init__(self, cursor):
                self.cursor = cursor
                self.lastrowid = 1

            def execute(self, sql, *exec_args, **exec_kwargs):
                if "hdc_vec_facts" in sql or "hdc_specular_vec_facts" in sql:
                    if "INSERT INTO" in sql or "SELECT" in sql:
                        raise sqlite3.OperationalError("no such table: hdc_vec_facts")
                if "vec_distance_cosine" in sql:
                     raise sqlite3.OperationalError("no such module: vec0")
                return self.cursor.execute(sql, *exec_args, **exec_kwargs)

            def fetchall(self):
                return self.cursor.fetchall()

            def fetchone(self):
                return self.cursor.fetchone()

        def mocked_cursor():
            return MockCursor(original_cursor())

        # Instead of modifying the native connection directly, we wrap it in a mock object
        mock_conn = MagicMock()
        mock_conn.execute = mocked_execute
        mock_conn.cursor = mocked_cursor
        mock_conn.commit = conn.commit
        return mock_conn

    with patch("cortex.memory.hdc.store.sqlite3.connect", side_effect=mocked_connect):
        conn = mock_store._get_conn()

        # Test Memorize (Insert fallback)
        fact = CortexFactModel(
            tenant_id="default",
            project_id="default",
            content="HDC Fact test fallback",
            embedding=[0.1] * 128,
            metadata={},
        )

        # Should not crash
        await mock_store.memorize(fact)

        # Test Recall Secure (Select fallback)
        res = await mock_store.recall_secure("default", "default", "test query")
        assert res == [] # Since vec0 query fails, it returns empty

    await mock_store.close()
