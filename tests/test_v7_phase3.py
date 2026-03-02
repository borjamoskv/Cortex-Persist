import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from cortex.engine.growth import NeuralGrowthEngine
from cortex.engine.endocrine import ENDOCRINE, HormoneType

@pytest.mark.asyncio
async def test_growth_engine_promotion():
    conn = AsyncMock() # Use AsyncMock for conn
    # Mock facts: 3 projects having the same bridge content
    cursor = AsyncMock()
    cursor.fetchall = AsyncMock(return_value=[
        ("Pattern: Red Team immunity", 3)
    ])
    conn.execute = AsyncMock(return_value=cursor)
    conn.commit = AsyncMock()
    
    # Set growth high enough for promotion
    ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 1.0) 
    
    engine = NeuralGrowthEngine()
    
    # Test without storer (fallback to direct insert)
    promoted = await engine._promote_successful_bridges(conn)
    assert promoted == 1
    assert conn.execute.called

@pytest.mark.asyncio
async def test_growth_engine_consolidation():
    conn = AsyncMock() # Use AsyncMock for conn
    # Mock duplicates
    cursor = AsyncMock()
    cursor.fetchall = AsyncMock(side_effect=[
        [("projectA", "bridge_content", 2)], # Outer loop
        [(101,), (102,)] # Inner loop
    ])
    conn.execute = AsyncMock(return_value=cursor)
    conn.commit = AsyncMock()
    
    engine = NeuralGrowthEngine()
    consolidated = await engine._consolidate_redundant_facts(conn)
    
    assert consolidated == 1 # 2 dupes minus 1 master = 1 deprecated
