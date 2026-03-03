"""Concurrency and Race Condition tests for MomentumEngine (Ω₅).

Ensures that even under task cancellation or abrupt failure, 
connections are closed and the state remains consistent.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from scripts.momentum_engine import MomentumEngine

@pytest.mark.asyncio
async def test_engage_one_resilience_to_cancellation():
    """Verify that client.close() is ALWAYS called, even if the task is cancelled during sleep."""
    identity = {"name": "ghost-1", "api_key": "sk_test"}
    engine = MomentumEngine()
    
    # We want to capture the specific mock client instance created inside engage_one
    mock_client = AsyncMock()
    
    # Use a synchronization event to control exactly when we cancel
    jitter_started = asyncio.Event()
    
    async def mock_sleep(duration):
        jitter_started.set()
        await asyncio.sleep(100) # Sleep long enough to be cancelled

    with patch("scripts.momentum_engine.MoltbookClient", return_value=mock_client), \
         patch("scripts.momentum_engine.asyncio.sleep", side_effect=mock_sleep):
        
        # Start engagement
        task = asyncio.create_task(engine.engage_one("post_123", identity))
        
        # Wait until it hits the jitter (sleep)
        await jitter_started.wait()
        
        # ACT: Cancel the task while it's in the middle of the try block
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
            
    # ASSERT: Finally block must have executed
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_boost_latest_task_group_simulated_failure():
    """Verify that if one agent fails, others continue and everything closes (TaskGroup behavior)."""
    engine = MomentumEngine()
    
    # Mock vault with two identities
    engine.vault = MagicMock()
    engine.vault.list_identities.return_value = [
        {"name": "agent-ok", "api_key": "sk_ok"},
        {"name": "agent-fail", "api_key": "sk_fail"},
    ]
    
    # Mock dependencies to isolate tests
    with patch("scripts.momentum_engine.MoltbookClient") as MockClient:
        # Create distinct mocks for each agent
        ok_client = AsyncMock()
        fail_client = AsyncMock()
        
        # The first instance created (admin_client in boost_latest)
        admin_client = AsyncMock()
        admin_client.get_profile.return_value = {"posts": [{"id": "p1"}]}
        
        # Side effect to return admin first, then agent clients
        MockClient.side_effect = [admin_client, ok_client, fail_client]
        
        # fail_client will raise an error during engagement
        ok_client.upvote_post.return_value = None
        fail_client.upvote_post.side_effect = Exception("Atomic failure")

        # Mock random jitter to 0
        with patch("scripts.momentum_engine.random.uniform", return_value=0), \
             patch("scripts.momentum_engine.random.random", return_value=0.5): # random < 0.3 fallback check
            
            await engine.boost_latest()

        # Check outcomes
        assert ok_client.upvote_post.called
        assert fail_client.upvote_post.called
        
        # CRITICAL: Both must be closed
        ok_client.close.assert_called_once()
        fail_client.close.assert_called_once()
        admin_client.close.assert_called_once()

from unittest.mock import MagicMock
