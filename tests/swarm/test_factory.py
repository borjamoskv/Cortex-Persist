from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.ledger.core import SovereignLedger
from cortex.swarm.discovery import SkillRegistry
from cortex.swarm.factory import SwarmFactory
from cortex.swarm.manager import SwarmManager


@pytest.fixture
def mock_ledger():
    ledger = MagicMock(spec=SovereignLedger)
    ledger.record_transaction = AsyncMock()
    return ledger

@pytest.fixture
def mock_registry():
    registry = MagicMock(spec=SkillRegistry)
    registry.find_skills_by_category.return_value = []
    # Mock para asegurar que find_skills_by_category devuelve algo iterable
    return registry

@pytest.fixture
def mock_manager(mock_ledger):
    manager = MagicMock(spec=SwarmManager)
    manager.ledger = mock_ledger
    manager.register_actuator = MagicMock()
    return manager

@pytest.mark.asyncio
async def test_factory_initialization(mock_registry, mock_manager):
    factory = SwarmFactory(registry=mock_registry, manager=mock_manager)
    assert "P0" in factory.QUADRANTS

@pytest.mark.asyncio
async def test_recruit_squad(mock_registry, mock_manager):
    # Setup mock to return some skills
    mock_skill = {"name": "test_specialist", "potency": 0.8}
    mock_registry.find_skills_by_category.return_value = [mock_skill]
    
    factory = SwarmFactory(registry=mock_registry, manager=mock_manager)
    
    skills = await factory.recruit_squad("P0", size=1)
    
    assert len(skills) == 1
    assert skills[0]["name"] == "test_specialist"
    mock_manager.register_actuator.assert_called_once()
    
    justification = factory.justify_recruitment("P0", skills)
    assert "Exergy Target: 12.5" in justification
    assert "Estimated Yield: 8.0" in justification

def test_get_quadrant_skills(mock_registry, mock_manager):
    mock_skill = {"name": "test_skill", "path": "/fake/path"}
    mock_registry.find_skills_by_category.return_value = [mock_skill]
    
    factory = SwarmFactory(registry=mock_registry, manager=mock_manager)
    skills = factory.get_quadrant_skills("P0")
    
    # Due to dedup logic and P0 having 3 categories, it should return 1 unique skill
    assert len(skills) == 1
    assert skills[0]["name"] == "test_skill"
