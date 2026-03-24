from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.services.bounty_service import BountyLead, BountyService
from cortex.swarm.bridges.bounty_bridge import BountySwarmBridge
from cortex.swarm.factory import SwarmFactory
from cortex.swarm.manager import SwarmManager


@pytest.mark.asyncio
async def test_bounty_swarm_bridge_activation():
    """Test the full kinetic workflow of the BountySwarmBridge."""
    
    # 1. Setup Mocks
    mock_ledger = MagicMock()  # Ledger is now synchronous in v8
    mock_manager = MagicMock(spec=SwarmManager)
    mock_manager.ledger = mock_ledger
    mock_manager.shard_task = AsyncMock(return_value=[{"status": "success", "metadata": {}}])
    
    mock_factory = AsyncMock(spec=SwarmFactory)
    mock_factory.recruit_squad = AsyncMock(return_value=["agent-1", "agent-2"])
    
    # Mock BountyService
    mock_lead = BountyLead(
        number=101,
        title="Test Bounty",
        url="http://test.com/101",
        reward_usd=Decimal("500.0"),
        difficulty="medium",
        score=Decimal("9.0"),
        repo="owner/repo"
    )
    
    mock_bounty_service = MagicMock(spec=BountyService)
    mock_bounty_service.scan_repository = AsyncMock(return_value=[mock_lead])
    mock_bounty_service.rank_leads = MagicMock(return_value=[mock_lead])
    mock_bounty_service.generate_claim_prompt = MagicMock(return_value="Solve this!")
    
    # 2. Instantiate Bridge
    bridge = BountySwarmBridge(
        bounty_service=mock_bounty_service,
        factory=mock_factory,
        manager=mock_manager
    )
    
    # 3. Execute Bridge
    result = await bridge.bridge_high_exergy_bounties("owner", "repo", squad_size=2)
    
    # 4. Verify Workflow
    assert result["status"] == "kinetic_active"
    assert result["leads_processed"] == 1
    
    # Verify Recruitment
    mock_factory.recruit_squad.assert_awaited_once_with("frontline", size=2)
    
    # Verify Sharding
    mock_manager.shard_task.assert_awaited_once_with(["agent-1", "agent-2"], "Solve this!")
    
    # Verify Ledger Recording
    mock_ledger.record_transaction.assert_called_once()
    args, kwargs = mock_ledger.record_transaction.call_args
    assert kwargs["action"] == "kinetic_bridge_activation"
    assert kwargs["detail"]["bounty_id"] == 101
    assert "mechanical_justification" in kwargs["detail"]
    assert "Kinetic bridge triggered" in kwargs["detail"]["mechanical_justification"]


@pytest.mark.asyncio
async def test_bounty_swarm_bridge_no_leads():
    """Test the bridge when no high-exergy leads are found."""
    mock_bounty_service = MagicMock(spec=BountyService)
    mock_bounty_service.scan_repository = AsyncMock(return_value=[])
    mock_bounty_service.rank_leads = MagicMock(return_value=[])
    
    bridge = BountySwarmBridge(
        bounty_service=mock_bounty_service,
        factory=MagicMock(),
        manager=MagicMock()
    )
    
    result = await bridge.bridge_high_exergy_bounties("owner", "repo")
    
    assert result["status"] == "idle"
    assert result["leads_processed"] == 0
