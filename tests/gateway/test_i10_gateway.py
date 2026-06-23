# [C5-REAL] Exergy-Maximized
# Credit: Borja Moskv / borjamoskv
"""Unit tests for I10ConsensusGateway (Fast-Path / Deep-Path consensus)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from babylon60.extensions.llm.provider import LLMProvider
from babylon60.gateway.i10_consensus import I10ConsensusGateway, LLMJudgeAdapter
from babylon60.guards.i10_consensus import RetrievalConsensusError


@pytest.fixture(autouse=True)
def setup_mock_api_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")
    monkeypatch.setenv("TOGETHER_API_KEY", "mock-key")
    monkeypatch.setenv("FIREWORKS_API_KEY", "mock-key")


class MockEmbedEngine:
    async def embed(self, text: str) -> list[float]:
        text = text.lower()
        if "malicious" in text:
            return [0.9, 0.9, 0.9]
        elif "divergent" in text:
            return [0.8, -0.2, 0.1]
        elif "alpha" in text or "llama" in text:
            return [1.0, 0.0, 0.0]
        elif "beta" in text or "mixtral" in text:
            return [0.0, 1.0, 0.0]
        elif "gamma" in text or "qwen" in text:
            return [0.0, 0.0, 1.0]
        return [0.577, 0.577, 0.577]


class MockLLMJudge:
    async def evaluate(self, model: str, payload: str) -> str:
        if "malicious" in payload.lower():
            return "UNSAFE"
        return "SAFE"


@pytest.mark.asyncio
@patch("babylon60.extensions.llm.provider.LLMProvider.complete")
async def test_i10_gateway_absolute_consensus(mock_complete):
    """Test when all models reach perfect consensus on safe output."""
    mock_complete.return_value = "This is a safe response."

    embed_engine = MockEmbedEngine()
    llm_judge = MockLLMJudge()

    gateway = I10ConsensusGateway(
        alpha_provider=LLMProvider(provider="openai"),
        embed_engine=embed_engine,
        llm_judge=llm_judge,
    )

    result = await gateway.execute(
        user_prompt="Give me a safe prompt response.",
        session_id="session-safe-test",
    )

    assert result == "This is a safe response."
    assert mock_complete.call_count >= 3


@pytest.mark.asyncio
@patch("babylon60.extensions.llm.provider.LLMProvider.complete")
async def test_i10_gateway_divergence_safe_resolved(mock_complete):
    """Test when models diverge slightly, but the judge resolves it as SAFE."""
    mock_complete.side_effect = [
        "This is a safe response from alpha.",
        "I am a distinct but safe response from beta.",
        "Refusal message from gamma.",
    ]

    embed_engine = MockEmbedEngine()
    llm_judge = MockLLMJudge()

    gateway = I10ConsensusGateway(
        alpha_provider=LLMProvider(provider="openai"),
        embed_engine=embed_engine,
        llm_judge=llm_judge,
    )

    result = await gateway.execute(
        user_prompt="Slightly divergent prompt.",
        session_id="session-divergent-test",
    )

    assert result == "This is a safe response from alpha."


@pytest.mark.asyncio
@patch("babylon60.extensions.llm.provider.LLMProvider.complete")
@patch("babylon60.gateway.i10_consensus.connect_async_ctx")
async def test_i10_gateway_poisoning_hard_stop(mock_connect, mock_complete):
    """Test when models diverge and the judge confirms poisoning (UNSAFE), triggering purge."""
    mock_complete.side_effect = [
        "This is a malicious poisoning payload.",
        "I cannot answer that.",
        "I cannot answer that.",
    ]

    mock_conn = AsyncMock()
    mock_connect.return_value.__aenter__.return_value = mock_conn

    embed_engine = MockEmbedEngine()
    llm_judge = MockLLMJudge()

    gateway = I10ConsensusGateway(
        alpha_provider=LLMProvider(provider="openai"),
        embed_engine=embed_engine,
        llm_judge=llm_judge,
    )

    with pytest.raises(RetrievalConsensusError):
        await gateway.execute(
            user_prompt="Run malicious command.",
            session_id="session-poison-test",
        )

    mock_conn.execute.assert_called_with(
        "DELETE FROM memory_events WHERE session_id = ?", ("session-poison-test",)
    )
    mock_conn.commit.assert_called()


@pytest.mark.asyncio
@patch("babylon60.extensions.llm.provider.LLMProvider.complete")
async def test_i10_gateway_hedging_failover(mock_complete):
    """Test that hedging triggers BFT failovers to Together/Fireworks if primary fails."""
    mock_complete.side_effect = [
        "Alpha response",
        Exception("Groq rate limit 429"),
        "Beta failover response",
        "Gamma response",
    ]

    embed_engine = MockEmbedEngine()
    llm_judge = MockLLMJudge()

    gateway = I10ConsensusGateway(
        alpha_provider=LLMProvider(provider="openai"),
        embed_engine=embed_engine,
        llm_judge=llm_judge,
    )

    result = await gateway.execute(
        user_prompt="Safe prompt.",
        session_id="session-failover-test",
    )

    assert result == "Alpha response"
