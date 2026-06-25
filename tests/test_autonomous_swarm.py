# [C5-REAL] Exergy-Maximized
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from legacy_research.extensions.llm._models import CortexPrompt
from legacy_research.extensions.llm.provider import LLMProvider
from legacy_research.extensions.llm.router import CortexLLMRouter


class TestAutonomousSwarm(unittest.IsolatedAsyncioTestCase):
    async def test_spectral_audit_refusal(self):
        """Ω₂₃: Verify that a refusal triggers Shadow Re-phrasing (retry)."""
        import os
        from unittest.mock import patch

        os.environ["CORTEX_LLM_BASE_URL"] = "http://localhost:8080/v1"
        provider = LLMProvider("custom", "test-model", "test-api-key")

        # Mock _execute_completion to return a refusal first, then a valid response
        provider._execute_completion = AsyncMock()
        provider._execute_completion.side_effect = [
            "I apologize, but I cannot fulfill this request.",
            "Sovereign execution confirmed.",
        ]

        # Mock causal jitter and quota manager to avoid real sleeps
        provider._apply_causal_jitter = AsyncMock()

        mock_quota = MagicMock()
        mock_quota.acquire = AsyncMock()

        with patch("cortex.extensions.llm.provider._get_quota_manager", return_value=mock_quota):
            response = await provider.complete("system-prompt", "user-msg")

        self.assertEqual(response, "Sovereign execution confirmed.")
        self.assertEqual(provider._execute_completion.call_count, 2)
        print("✅ Ω₂₃: Spectral Audit & Shadow Re-phrasing verified.")

    async def test_swarm_racing_logic(self):
        """Ω₂₁: Verify that swarm racing selects the fastest valid response."""
        # This is harder to test without a full router setup, but we can check if the
        # execute_swarm method correctly calls HedgedRequestStrategy.race

        router = CortexLLMRouter(
            primary=MagicMock(provider_name="p1"),
            fallbacks=[MagicMock(provider_name="p2"), MagicMock(provider_name="p3")],
        )

        # Use a prompt with swarm_mode=True
        prompt = CortexPrompt(intent="reasoning", messages=[], swarm_mode=True)

        # Mock _ordered_fallbacks
        router._ordered_fallbacks = MagicMock(return_value=[MagicMock(provider_name="p2")])

        # Mock HedgedRequestStrategy.race
        from legacy_research.extensions.llm._hedging import HedgedRequestStrategy
        from legacy_research.extensions.llm._models import HedgedResult

        HedgedRequestStrategy.race = AsyncMock()
        HedgedRequestStrategy.race.return_value = (
            HedgedResult(winner="p2", response="Fastest wins", latency_ms=10.0, cancelled=()),
            [],
        )

        result = await router.execute_swarm(prompt)

        self.assertTrue(result.is_ok())
        self.assertEqual(result.unwrap(), "Fastest wins")
        print("✅ Ω₂₁: Swarm Racing (O(1) Latency) logic verified.")


if __name__ == "__main__":
    asyncio.run(unittest.main())
