"""Tests for CORTEX Epistemic Lineage & Audit Protocols (Ω₃-V)."""

import pytest
from cortex.engine import CortexEngine
from cortex.core.lineage import LineageVerifier

@pytest.fixture
async def engine():
    engine = CortexEngine(":memory:", auto_embed=False)
    await engine.init_db()
    
    # Mock search to avoid deduplication logic triggering schema errors
    async def mock_search(*args, **kwargs):
        return []
    engine.facts.search = mock_search
    
    yield engine
    await engine.close()

@pytest.mark.asyncio
async def test_fact_lineage_tracing(engine):
    # 1. Create L0 Ground Truth
    f0_id = await engine.store(
        project="test_proj",
        content="The Earth is round.",
        fact_type="knowledge",
        confidence="C5"
    )
    
    # 2. Create L1 Inferred Fact
    f1_id = await engine.store(
        project="test_proj",
        content="Since the Earth is round, ships disappear hull-first.",
        fact_type="axiom",
        meta={"lineage_sources": [f0_id]}
    )
    
    # 3. Create L2 Synthesized Insight
    f2_id = await engine.store(
        project="test_proj",
        content="Curvature is the reason for the horizon's limits.",
        fact_type="knowledge",
        meta={"lineage_sources": [f1_id]}
    )
    
    verifier = LineageVerifier(engine)
    root = await verifier.get_lineage(f2_id)
    
    # Verify tree structure
    assert root.fact_id == f2_id
    assert len(root.parents) == 1
    assert root.parents[0].fact_id == f1_id
    assert len(root.parents[0].parents) == 1
    assert root.parents[0].parents[0].fact_id == f0_id
    assert root.is_valid is True

@pytest.mark.asyncio
async def test_broken_lineage(engine):
    # Store a fact pointing to a non-existent parent
    f_id = await engine.store(
        project="test_proj",
        content="A conclusion with no base.",
        fact_type="knowledge",
        meta={"lineage_sources": [99999]}
    )
    
    verifier = LineageVerifier(engine)
    root = await verifier.get_lineage(f_id)
    
    assert root.is_valid is True # The fact itself is valid L0 record
    assert len(root.parents) == 1
    assert root.parents[0].is_valid is False
    assert "Fact not found" in root.parents[0].error

@pytest.mark.asyncio
async def test_file_audit_regex():
    # Helper to test the re logic used in audit-file
    import re
    content = """
    Based on Fact #101 and Fact #102, we conclude X.
    Also refer to #103 for details.
    """
    fact_ids = [int(fid) for fid in re.findall(r"(?:Fact\s+)?#(\d+)", content)]
    assert set(fact_ids) == {101, 102, 103}
