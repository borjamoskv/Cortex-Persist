# [C5-REAL] Exergy-Maximized
# Author: borjamoskv
# License: Apache-2.0
"""
Verification suite for babylon60/extensions/training/moskv1_core.py.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from babylon60.extensions.training.moskv1_core import (
    ConversationTurn,
    InferenceResult,
    MOSKV1Core,
    RetrievedContext,
)


def test_conversation_history_operations():
    """Verify history manipulation in MOSKV1Core."""
    core = MOSKV1Core(max_history=3)
    assert len(core._history) == 0

    core.add_to_history("user", "Hello")
    core.add_to_history("assistant", "Hi")
    assert len(core._history) == 2
    assert core._history[0].role == "user"
    assert core._history[0].content == "Hello"
    assert core._history[1].role == "assistant"
    assert core._history[1].content == "Hi"

    core.clear_history()
    assert len(core._history) == 0


def test_assemble_prompt_structure():
    """Verify system, context, history, and query assembly in the prompt."""
    core = MOSKV1Core()
    core.add_to_history("user", "Previous question")
    core.add_to_history("assistant", "Previous answer")

    context = RetrievedContext(
        facts=[
            {
                "content": "Verified fact 1",
                "project": "Alpha",
                "confidence": "high",
                "score": 0.95,
                "source": "hybrid_search",
            }
        ],
        total_tokens_estimate=10,
        retrieval_score=0.95,
        vault_entries=["Vault entry content"],
    )

    payload = core.assemble_prompt(
        user_query="Current query",
        context=context,
        include_system=True,
        include_history=True,
    )
    messages = payload["messages"]

    # Verify order: system -> context -> assistant confirm -> history -> query
    assert messages[0]["role"] == "system"
    assert "MOSKV-1 APEX" in messages[0]["content"]

    assert messages[1]["role"] == "user"
    assert "Verified fact 1" in messages[1]["content"]
    assert "Vault entry content" in messages[1]["content"]

    assert messages[2]["role"] == "assistant"
    assert "Contexto asimilado" in messages[2]["content"]

    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "Previous question"

    assert messages[4]["role"] == "assistant"
    assert messages[4]["content"] == "Previous answer"

    assert messages[5]["role"] == "user"
    assert messages[5]["content"] == "Current query"


@pytest.mark.asyncio
async def test_warmup_no_adapters(tmp_path):
    """Verify warmup returns False immediately if no adapter weights exist."""
    core = MOSKV1Core()
    core._adapter_path = tmp_path / "nonexistent"
    result = await core.warmup()
    assert result is False


@pytest.mark.asyncio
async def test_infer_mlx_success():
    """Verify infer returns MLX result when _mlx_chat succeeds."""
    core = MOSKV1Core()

    # Mock retrieve_context
    mock_context = RetrievedContext(
        facts=[],
        total_tokens_estimate=0,
        retrieval_score=0.0,
        vault_entries=[],
    )
    core.retrieve_context = AsyncMock(return_value=mock_context)

    # Mock _mlx_chat to succeed
    core._mlx_chat = AsyncMock(return_value="MLX success response")

    result = await core.infer(
        user_query="Test query",
        db_conn=MagicMock(),
        record_history=True,
    )

    assert isinstance(result, InferenceResult)
    assert result.response == "MLX success response"
    assert result.model_used == "mlx_native_lora"
    assert result.fallback_used is False
    assert len(core._history) == 2


@pytest.mark.asyncio
async def test_infer_fallbacks():
    """Verify fallback sequence: MLX -> Ollama MOSKV-1 -> Ollama base -> SovereignLLM."""
    core = MOSKV1Core()

    # Mock retrieve_context
    mock_context = RetrievedContext(
        facts=[],
        total_tokens_estimate=0,
        retrieval_score=0.0,
        vault_entries=[],
    )
    core.retrieve_context = AsyncMock(return_value=mock_context)

    # Case 1: MLX fails, Ollama MOSKV-1 succeeds
    core._mlx_chat = AsyncMock(return_value="[ERROR] MLX failed")
    core._ollama_chat = AsyncMock(
        side_effect=lambda messages, temp, model_override=None: (
            "Ollama MOSKV-1 response" if model_override is None else "[ERROR] base failed"
        )
    )

    result = await core.infer(
        user_query="Test query",
        db_conn=MagicMock(),
        record_history=False,
    )
    assert result.response == "Ollama MOSKV-1 response"
    assert result.model_used == core.model_name
    assert result.fallback_used is True

    # Case 2: MLX and Ollama MOSKV-1 fail, Ollama base succeeds
    core._ollama_chat = AsyncMock(
        side_effect=lambda messages, temp, model_override=None: (
            "[ERROR] MOSKV-1 failed" if model_override is None else "Ollama base response"
        )
    )

    result = await core.infer(
        user_query="Test query",
        db_conn=MagicMock(),
        record_history=False,
    )
    assert result.response == "Ollama base response"
    assert result.model_used == "qwen2.5-coder:32b-instruct-q4_K_M"
    assert result.fallback_used is True

    # Case 3: Ollama fails entirely, SovereignLLM succeeds
    core._ollama_chat = AsyncMock(return_value="[ERROR] Ollama completely failed")
    core._sovereign_fallback = AsyncMock(return_value="SovereignLLM response")

    result = await core.infer(
        user_query="Test query",
        db_conn=MagicMock(),
        record_history=False,
    )
    assert result.response == "SovereignLLM response"
    assert result.model_used == "sovereign_llm"
    assert result.fallback_used is True


def test_get_modelfile():
    """Verify Ollama Modelfile generation includes system prompt."""
    core = MOSKV1Core()
    modelfile = core.get_modelfile()
    assert "FROM qwen2.5-coder:32b-instruct-q4_K_M" in modelfile
    assert "Eres MOSKV-1 APEX" in modelfile
    assert "PARAMETER temperature 0.0" in modelfile


@pytest.mark.asyncio
async def test_check_ollama_health_mock():
    """Verify health check parses tags correctly."""
    core = MOSKV1Core()

    class MockResponse:
        def __init__(self, status, json_data):
            self.status = status
            self._json_data = json_data

        async def json(self):
            return self._json_data

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_json = {
        "models": [
            {"name": "moskv1-core:32b-q4_K_M"},
            {"name": "qwen2.5-coder:32b-instruct-q4_K_M"},
        ]
    }

    # Patch aiohttp.ClientSession.get to return MockResponse
    with patch("aiohttp.ClientSession.get", return_value=MockResponse(200, mock_json)):
        health = await core.check_ollama_health()
        assert health["ollama_reachable"] is True
        assert health["moskv1_available"] is True
        assert health["fallback_available"] is True
        assert "moskv1-core:32b-q4_K_M" in health["models"]
