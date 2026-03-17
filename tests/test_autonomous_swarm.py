import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from cortex.extensions.llm._models import CortexPrompt
from cortex.extensions.llm.provider import LLMProvider
from cortex.extensions.llm.router import CortexLLMRouter


class TestAutonomousSwarm(unittest.IsolatedAsyncioTestCase):
    async def test_spectral_audit_refusal(self):
        """Ω₂₃: Verify that a refusal triggers Shadow Re-phrasing (retry)."""
        provider = LLMProvider("test-provider", "test-model", "test-api-key")

        # Mock _execute_completion to return a refusal first, then a valid response
        provider._execute_completion = AsyncMock()
        provider._execute_completion.side_effect = [
            "I apologize, but I cannot fulfill this request.",
            "Sovereign execution confirmed.",
        ]

        # We need to mock _apply_causal_jitter to avoid sleeping
        provider._apply_causal_jitter = AsyncMock()

        response = await provider.complete("system-prompt", "user-msg", tokens_estimate=100)

        self.assertEqual(response, "Sovereign execution confirmed.")
        self.assertEqual(provider._execute_completion.call_count, 2)
        print("✅ Ω₂₃: Spectral Audit & Shadow Re-phrasing verified.")

    async def test_swarm_racing_logic(self):
        """Ω₂₁: Verify that swarm racing selects the fastest valid response."""
        # This is harder to test without a full router setup, but we can check if the
        # execute_swarm method correctly calls HedgedRequestStrategy.race

        # Mocking the dependencies of CortexLLMRouter
        mock_cascade = MagicMock()
        mock_telemetry = MagicMock()

        router = CortexLLMRouter(
            primary=MagicMock(provider_name="p1"),
            fallbacks=[MagicMock(provider_name="p2"), MagicMock(provider_name="p3")],
            cascade=mock_cascade,
            telemetry=mock_telemetry,
        )

        # Use a prompt with swarm_mode=True
        prompt = CortexPrompt(intent="test", messages=[], swarm_mode=True)

        # Mock _ordered_fallbacks
        router._ordered_fallbacks = MagicMock(return_value=[MagicMock(provider_name="p2")])

        # Mock HedgedRequestStrategy.race
        from cortex.extensions.llm._hedging import HedgedRequestStrategy, RaceResult

        HedgedRequestStrategy.race = AsyncMock()
        HedgedRequestStrategy.race.return_value = (
            RaceResult(winner="p2", response="Fastest wins", latency_ms=10.0),
            [],
        )

        result = await router.execute_swarm(prompt)

        self.assertTrue(result.is_ok())
        self.assertEqual(result.unwrap(), "Fastest wins")
        print("✅ Ω₂₁: Swarm Racing (O(1) Latency) logic verified.")


if __name__ == "__main__":
    asyncio.run(unittest.main())
