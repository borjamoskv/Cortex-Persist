from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.extensions.mejoralo.models import DimensionResult, ScanResult
from cortex.swarm.actuators.protocol import ActuatorResponse
from cortex.swarm.bridges.evolution_bridge import EvolutionSwarmBridge


@pytest.mark.asyncio
async def test_evolution_bridge_cycle():
    # 1. Setup Mocks
    mock_engine = MagicMock()
    mock_mejoralo = MagicMock()
    mock_factory = AsyncMock()
    mock_manager = AsyncMock()
    mock_ledger = MagicMock()
    
    mock_manager.ledger = mock_ledger
    
    bridge = EvolutionSwarmBridge(
        engine=mock_engine,
        mejoralo=mock_mejoralo,
        factory=mock_factory,
        manager=mock_manager
    )
    
    # Mock Scan Result with a finding
    mock_scan_before = ScanResult(
        project="test_proj",
        stack="python",
        score=70,
        dimensions=[
            DimensionResult(
                name="Complejidad",
                score=60,
                weight="high",
                findings=["cortex/engine.py:10 -> High Complexity (15) in 'run'"]
            )
        ],
        dead_code=False
    )
    
    mock_scan_after = ScanResult(
        project="test_proj",
        stack="python",
        score=90,
        dimensions=[],
        dead_code=False
    )
    
    mock_mejoralo.scan.side_effect = [mock_scan_before, mock_scan_after]
    mock_factory.recruit_squad.return_return_value = ["agent-01"]
    mock_factory.recruit_squad.return_value = ["agent-01"]
    
    mock_manager.shard_task.return_value = [
        ActuatorResponse(content="optimized_code", status="success")
    ]
    
    # Mock file writing to avoid I/O
    with patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "write_text") as mock_write:
        
        # 2. Execute
        result = await bridge.evolve_project("test_proj", "/tmp/test_proj", threshold=80)
        
        # 3. Assertions
        assert result["status"] == "completed"
        assert result["score_before"] == 70
        assert result["score_after"] == 90
        assert result["delta"] == 20
        assert len(result["mutations"]) == 1
        assert result["mutations"][0]["file"] == "cortex/engine.py"
        
        # Verify Factory was called
        mock_factory.recruit_squad.assert_called_once()
        objective = mock_factory.recruit_squad.call_args[0][0]
        assert "cortex/engine.py" in objective
        
        # Verify Manager was called
        mock_manager.shard_task.assert_called_once()
        prompt = mock_manager.shard_task.call_args[0][1]
        assert "High Complexity (15) in 'run'" in prompt
        
        # Verify Write occurred
        mock_write.assert_called_with("optimized_code")
        
        # Verify Ledger
        mock_ledger.record_transaction.assert_called()
        mock_mejoralo.record_session.assert_called()

@pytest.mark.asyncio
async def test_evolution_bridge_skips_if_perfect():
    mock_mejoralo = MagicMock()
    bridge = EvolutionSwarmBridge(MagicMock(), mock_mejoralo, AsyncMock(), AsyncMock())
    
    mock_mejoralo.scan.return_value = ScanResult(
        project="perfect", score=100, dimensions=[], dead_code=False, stack="python"
    )
    
    result = await bridge.evolve_project("perfect", "/tmp/perfect")
    assert result["status"] == "skipped"
