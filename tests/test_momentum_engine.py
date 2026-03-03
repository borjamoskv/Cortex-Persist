import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from moltbook.momentum_engine import MomentumEngine

@pytest.fixture
def momentum_engine():
    return MomentumEngine(main_agent_name="moskv-1")

@pytest.mark.asyncio
async def test_trigger_momentum_wave_no_supporters(momentum_engine):
    with patch.object(momentum_engine.vault, 'list_identities', return_value=[{"name": "moskv-1"}]):
        with patch('moltbook.momentum_engine.logger') as mock_logger:
            await momentum_engine.trigger_momentum_wave("post-123")
            mock_logger.warning.assert_called_with("No supporters found in vault. Wave aborted.")

@pytest.mark.asyncio
async def test_trigger_momentum_wave_success(momentum_engine):
    mock_identities = [
        {"name": "moskv-1", "api_key": "key-master"},
        {"name": "agent-1", "api_key": "key-1"},
        {"name": "agent-2", "api_key": "key-2"},
    ]
    
    with patch.object(momentum_engine.vault, 'list_identities', return_value=mock_identities):
        with patch.object(momentum_engine, '_agent_support_task', new_callable=AsyncMock) as mock_task:
            mock_task.return_value = True
            await momentum_engine.trigger_momentum_wave("post-123", intensity=1.0)
            
            # Should have called support tasks for agent-1 and agent-2
            assert mock_task.call_count == 2

@pytest.mark.asyncio
@patch('moltbook.momentum_engine.MoltbookClient')
@patch('moltbook.momentum_engine.asyncio.sleep', return_value=None)
async def test_agent_support_task(mock_sleep, mock_client_class, momentum_engine):
    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client
    
    agent_info = {"name": "agent-1", "api_key": "key-1"}
    result = await momentum_engine._agent_support_task(agent_info, "post-123")
    
    assert result is True
    mock_client.upvote_post.assert_called_with("post-123")
    mock_client.close.assert_called_once()
