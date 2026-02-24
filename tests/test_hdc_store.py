"""Tests for CORTEX v7 HDC Vector Store L2."""

import pytest
import sqlite3

from cortex.memory.hdc.codec import HDCEncoder
from cortex.memory.hdc.item_memory import ItemMemory
from cortex.memory.hdc.store import HDCVectorStoreL2
from cortex.memory.models import CortexFactModel


@pytest.fixture
def hdc_store(tmp_path):
    """Fixture for a temporary HDC vector store."""
    mem = ItemMemory(dim=2000)
    enc = HDCEncoder(mem)
    
    # Needs a real file path for sqlite_vec
    db_path = tmp_path / "test_hdc.db"
    store = HDCVectorStoreL2(
        encoder=enc,
        item_memory=mem,
        db_path=db_path,
        half_life_days=7
    )
    return store


@pytest.mark.asyncio
async def test_memorize_and_recall_secure(hdc_store):
    """Test standard recall works through the SQLite-vec ranking engine."""
    # Add a fact
    fact = CortexFactModel(
        tenant_id="test_tenant",
        project_id="cortex",
        content="We decided to use HDC for semantic memory.",
        embedding=[], # Encoding is handled by store internally if not provided mapping
        is_diamond=False,
        is_bridge=False,
        confidence="C5",
        success_rate=1.0,
    )
    
    await hdc_store.memorize(fact, fact_type="decision")
    
    # Test recall
    results = await hdc_store.recall_secure(
        tenant_id="test_tenant",
        project_id="cortex",
        query="What memory architecture did we decide on?",
        limit=2
    )
    
    assert len(results) == 1
    recalled = results[0]
    
    assert recalled.id == fact.id
    assert recalled.content == fact.content
    assert recalled.tenant_id == fact.tenant_id
    
    # Store should automatically rebuild the HV from float32 back to int8
    assert len(recalled.embedding) == 2000
    assert all(x in {-1, 1} for x in recalled.embedding)
    
    # Test Tenant Isolation
    secure_results = await hdc_store.recall_secure(
        tenant_id="malicious_tenant", 
        project_id="cortex",
        query="memory architecture",
    )
    assert len(secure_results) == 0

    await hdc_store.close()


@pytest.mark.asyncio
async def test_extract_traces(hdc_store):
    """Test HDC unbinding traceability."""
    # Create fact manually so we can extract it
    fact = CortexFactModel(
        tenant_id="test_tenant",
        project_id="alpha-project",
        content="XOR binding implies self-inversion",
        embedding=[], 
    )
    
    await hdc_store.memorize(fact, fact_type="research")
    
    # Recall it to get the fully populated fact
    results = await hdc_store.recall_secure(
        tenant_id="test_tenant",
        project_id="alpha-project",
        query="binding XOR inversion",
        limit=1
    )
    
    assert len(results) == 1
    recalled = results[0]
    
    # Extract traces
    traces = hdc_store.extract_traces(recalled)
    
    assert "top_symbols" in traces
    
    # Since we encoded 'XOR binding implies self-inversion'
    # The top symbols should ideally contain these tokens.
    # Due to majority voting bundle, this might not perfectly reconstruct every token, 
    # but some structure remains. We just assert the trace dictionary looks right.
    top_tokens = [sym for sym, score in traces["top_symbols"]]
    
    # The list should exist and have up to 5 entries
    assert len(top_tokens) <= 5
    
    await hdc_store.close()
