from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.extensions.daemon.frontier import FrontierDaemon
from cortex.services.bounty_service import BountyService
from cortex.swarm.specialists import GoogleJulesOmega


@pytest.mark.asyncio
async def test_bounty_service_scan():
    service = BountyService(ledger=None)
    leads = await service.scan_repository("test_owner", "test_repo")
    assert len(leads) > 0
    assert leads[0].reward_usd == 500.0

@pytest.mark.asyncio
async def test_jules_actuator_execution():
    actuator = GoogleJulesOmega()
    response = await actuator.execute("Solve bug #42")
    assert "Jules AI" in response["content"]
    assert response["metadata"]["exergy_yield"] > 0

@pytest.mark.asyncio
async def test_frontier_daemon_ingestion_with_bounties():
    # Mock engine and ledger
    mock_engine = MagicMock()
    mock_engine.ledger = AsyncMock()
    
    daemon = FrontierDaemon(engine=mock_engine)
    daemon._log_evolution = MagicMock()
    
    # Run ingestion cycle
    await daemon._run_ingestion()
    
    # Verify that log_evolution was called for ingestion and bounty
    calls = [call.args[0] for call in daemon._log_evolution.call_args_list]
    assert "ingestion" in calls
    assert "bounty" in calls
