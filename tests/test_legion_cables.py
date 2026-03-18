import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.extensions.moltbook.legion_engine import (
    MoltbookLegionEngine,
)


@pytest.mark.asyncio
async def test_legion_cable_coordination():
    """
    Verifies that a Vanguard broadcast triggers a Shadow reaction via SubmarineCable.
    """
    # 1. Setup Engine with 1 Vanguard and 1 Shadow
    engine = MoltbookLegionEngine(agent_count=1, subagent_count=1, use_cables=True)

    # Use a high port to avoid conflicts
    engine.cable.port = 9991

    # 2. Mock Clients to avoid real networking/LLM
    mock_client = AsyncMock()
    mock_client.create_post.return_value = {"post": {"id": "test_post_123"}}
    mock_client.comment.return_value = {"status": "success"}

    for v in engine.vanguards:
        v.client = mock_client
        v.guard.report_429 = MagicMock()  # Mock anti-ban

    for s in engine.shadows:
        s.client = mock_client
        s.guard.report_429 = MagicMock()

    # 3. Patch LLM calls and sleep in agents to avoid billing/latency and timeouts
    with (
        patch("cortex.extensions.moltbook.legion_engine.LLMProvider") as mock_llm_provider,
        patch("cortex.extensions.moltbook.legion_engine.asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = "This is a synthetic comment."
        mock_llm_provider.return_value = mock_llm

        # 4. Initialize and Execute
        # We don't call full execute() because it has sequential logic we want to bypass for the reactive test
        await engine.cable.initialize()
        listener_task = asyncio.create_task(engine._cable_listener())

        # 5. Trigger Vanguard Action
        semaphore = asyncio.Semaphore(1)
        post_id = await engine.vanguards[0].act(semaphore, "general")

        assert post_id == "test_post_123"

        # 6. Wait for Shadow reaction
        # The listener should pick up the broadcast and trigger ShadowAgent.act
        # We wait a bit for the async task to propagate
        await asyncio.sleep(0.5)

        # Verify Shadow acted on the specific post_id
        # We check if mock_client.comment was called
        mock_client.comment.assert_called()
        args, kwargs = mock_client.comment.call_args
        assert kwargs.get("post_id") == "test_post_123"

        # 7. Cleanup
        engine._stop_signal.set()
        await asyncio.wait_for(listener_task, timeout=1.0)
        await engine.cable.shutdown()


if __name__ == "__main__":
    asyncio.run(test_legion_cable_coordination())
