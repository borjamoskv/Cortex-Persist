import pytest
import asyncio
from cortex.engine.legion import LegionOmegaEngine, AttackVector
from cortex.engine.vault import ConceptVault
import os

@pytest.fixture
def clean_vault():
    db_path = "test_legion_v62.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.mark.asyncio
async def test_v62_maxwell_rejection(clean_vault):
    engine = LegionOmegaEngine(max_cycles=1, db_path=clean_vault)
    
    # Intent that triggers a low-exergy response (simulated)
    # We'll use an intent name that our BlueTeam doesn't handle well
    # Actually, BlueTeam always generates some header.
    # We can mock the BlueTeam to return a "TODO" string.
    
    class LazyBlue:
        async def synthesize(self, *args):
            return "TODO pass"
            
    engine.blue_team = LazyBlue()
    
    result = await engine.forge("something complex")
    
    # Should fail due to Maxwell rejection before siege
    assert result.success is False
    assert any("MaxwellFilter" in f for f in result.vulnerabilities or [])

@pytest.mark.asyncio
async def test_v62_concept_persistence(clean_vault):
    engine = LegionOmegaEngine(max_cycles=3, db_path=clean_vault)
    
    # 1. Forge something and ensure it crystallizes
    # Mocking RedTeam to pass immediately for a specific intent
    class SoftRed:
        async def siege(self, code, context):
            return []
            
    engine.red_team.siege = SoftRed().siege
    
    intent = "secure_oauth_flow"
    result1 = await engine.forge(intent)
    assert result1.success is True
    assert result1.exergy >= 0.8
    
    # 2. Forge again with SAME intent, should use WARM_START
    # We can check the logs or just verify it works
    result2 = await engine.forge(intent)
    assert result2.success is True
    
    # Verify the vault has the concept
    concepts = engine.vault.get_all_concepts()
    assert any(c["intent"] == intent for c in concepts)
