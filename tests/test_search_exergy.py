import pytest
import time
import numpy as np
from unittest.mock import AsyncMock
from pathlib import Path
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2
from cortex.memory.models import CortexFactModel

@pytest.fixture
def temp_db_path(tmp_path):
    return tmp_path / "test_vec.db"

@pytest.fixture
def mock_encoder():
    encoder = AsyncMock()
    encoder.dimension = 384
    encoder.encode.return_value = [0.1] * 384
    return encoder

@pytest.mark.asyncio
async def test_exergy_prioritization(temp_db_path, mock_encoder):
    """
    Verifies that the new Causal Gradient Search correctly relies on exergy 
    to rank outputs when their semantic embeddings are identical.
    """
    store = SovereignVectorStoreL2(
        encoder=mock_encoder,
        db_path=temp_db_path,
        half_life_days=7
    )
    
    # Prepare identical embeddings so vector similarity is strictly equal
    embedding_vec = [0.1] * 384
    
    # 1. Memorize Low Exergy Fact (lots of stop words and decorative markers)
    # The guards are bypassed here since we directly insert to the store,
    # strictly testing retrieval mechanics.
    low_exergy_content = "por supuesto aquí tienes el código como un modelo de lenguaje"
    low_exergy_fact = CortexFactModel(
        id="fact_low_exergy",
        tenant_id="test_tenant",
        project_id="test_proj",
        content=low_exergy_content,
        embedding=embedding_vec,
        timestamp=time.time(),
        is_diamond=False,
        is_bridge=False,
        confidence="high",
        cognitive_layer="semantic",
        parent_decision_id=None,
        metadata={}
    )
    await store.memorize(low_exergy_fact)
    
    # 2. Memorize High Exergy Fact (dense, high information value)
    high_exergy_content = "cortex vector store exergy semantic search ranking"
    high_exergy_fact = CortexFactModel(
        id="fact_high_exergy",
        tenant_id="test_tenant",
        project_id="test_proj",
        content=high_exergy_content,
        embedding=embedding_vec,
        timestamp=time.time(),
        is_diamond=False,
        is_bridge=False,
        confidence="high",
        cognitive_layer="semantic",
        parent_decision_id=None,
        metadata={}
    )
    await store.memorize(high_exergy_fact)
    
    # 3. Recall
    # Since embeddings are identical, standard cosine sim is identical.
    # Exergy should elevate the purely factual record.
    results = await store.recall_secure(
        tenant_id="test_tenant",
        project_id="test_proj",
        query="search query ranking exergy",
        limit=2
    )
    
    assert len(results) == 2
    
    # High exergy must bubble to the top
    assert results[0].id == "fact_high_exergy"
    assert results[1].id == "fact_low_exergy"
    
    # And score differences should be explicit
    score_high = results[0]._recall_score
    score_low = results[1]._recall_score
    assert score_high > score_low

    await store.close()
