import unittest
from unittest.mock import AsyncMock

from cortex.sovereign.rem import InsightGenerator


class TestREMSynthesis(unittest.IsolatedAsyncioTestCase):
    async def test_synthesis_flow(self):
        # Mock Engine
        engine = AsyncMock()
        engine.recall.return_value = [
            {"content": "User initiated high-risk transaction."},
            {"content": "System detected unusual latency in Dimension B."},
            {"content": "Cortisol levels spike to 0.85."},
        ]
        engine.store.return_value = 12345

        # Mock LLM
        llm = AsyncMock()
        llm.complete.return_value = (
            "System experiencing high stress due to temporal anomalies."
        )

        generator = InsightGenerator(engine, llm)
        result = await generator.synthesize("test-project")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["fact_id"], 12345)
        self.assertIn("high stress", result["insight"])

        # Verify store call
        engine.store.assert_called_once()
        _, kwargs = engine.store.call_args
        self.assertEqual(kwargs["fact_type"], "insight")
        self.assertIn("rem", kwargs["tags"])


if __name__ == "__main__":
    unittest.main()
