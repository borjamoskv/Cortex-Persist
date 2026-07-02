# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.

"""Tests for ResilientGrokClient and ConversationHistory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
import openai
from pydantic import BaseModel, Field

from babylon60.extensions.llm.grok_client import ConversationHistory, ResilientGrokClient


class MockAnalysis(BaseModel):
    """Pydantic model representing structured audit findings for testing."""

    metric: str = Field(description="The metric name")
    value: int = Field(description="The numeric value")


def test_conversation_history_sliding_window() -> None:
    """Verifies that ConversationHistory respects the sliding window limit while preserving the system prompt."""
    history = ConversationHistory(system_prompt="System Prompt", max_messages=4)

    # 1. Check initial state
    msgs = history.get_messages()
    assert len(msgs) == 1
    assert msgs[0] == {"role": "system", "content": "System Prompt"}

    # 2. Add some messages within limit
    history.add_message("user", "Hello 1")
    history.add_message("assistant", "Hi 1")
    msgs = history.get_messages()
    assert len(msgs) == 3
    assert msgs[0]["role"] == "system"
    assert msgs[1] == {"role": "user", "content": "Hello 1"}
    assert msgs[2] == {"role": "assistant", "content": "Hi 1"}

    # 3. Exceed limit. max_messages = 4.
    # We add 2 more messages: total of 5 (1 system, 4 chat) -> must prune oldest chat message (Hello 1)
    history.add_message("user", "Hello 2")
    history.add_message("assistant", "Hi 2")

    msgs = history.get_messages()
    assert len(msgs) == 4
    # System prompt MUST still be present at index 0
    assert msgs[0] == {"role": "system", "content": "System Prompt"}
    # Oldest non-system message ("Hello 1") must be gone
    assert msgs[1] == {"role": "assistant", "content": "Hi 1"}
    assert msgs[2] == {"role": "user", "content": "Hello 2"}
    assert msgs[3] == {"role": "assistant", "content": "Hi 2"}


def test_conversation_history_clear() -> None:
    """Verifies clearing messages preserves the system prompt."""
    history = ConversationHistory(system_prompt="Keep Me", max_messages=10)
    history.add_message("user", "Clear Me")
    history.clear()

    msgs = history.get_messages()
    assert len(msgs) == 1
    assert msgs[0] == {"role": "system", "content": "Keep Me"}


@patch("babylon60.extensions.llm.grok_client.OpenAI")
def test_resilient_client_chat_success(mock_openai_class: MagicMock) -> None:
    """Verifies normal chat completion returns content."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Configure mock completion
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Respuesta de Grok"
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion

    client = ResilientGrokClient(api_key="test_key")
    result = client.chat("grok-4.20-multi-agent-beta-0309", [{"role": "user", "content": "test"}])

    assert result == "Respuesta de Grok"
    mock_client.chat.completions.create.assert_called_once()


@patch("babylon60.extensions.llm.grok_client.OpenAI")
def test_resilient_client_retry_on_rate_limit(mock_openai_class: MagicMock) -> None:
    """Verifies that ResilientGrokClient retries on RateLimitError and succeeds on subsequent try."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Configure mock behavior: raise RateLimitError first, then succeed
    mock_request = MagicMock()
    mock_response = MagicMock(status_code=429)
    rate_limit_err = openai.RateLimitError(
        message="Rate limit exceeded", response=mock_response, body=None
    )

    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Respuesta tras reintento"
    mock_completion.choices = [mock_choice]

    # Side effect: throw error, then return completion
    mock_client.chat.completions.create.side_effect = [rate_limit_err, mock_completion]

    client = ResilientGrokClient(api_key="test_key")

    # Temporarily set exponential multiplier to 0 for instantaneous tests
    with patch("tenacity.nap.time.sleep", return_value=None):
        result = client.chat(
            "grok-4.20-multi-agent-beta-0309", [{"role": "user", "content": "test"}]
        )

    assert result == "Respuesta tras reintento"
    assert mock_client.chat.completions.create.call_count == 2


@patch("babylon60.extensions.llm.grok_client.OpenAI")
def test_resilient_client_chat_structured(mock_openai_class: MagicMock) -> None:
    """Verifies that structured output is parsed into the requested Pydantic model."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_parsed_obj = MockAnalysis(metric="token_count", value=42)

    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.parsed = mock_parsed_obj
    mock_completion.choices = [mock_choice]

    mock_client.beta.chat.completions.parse.return_value = mock_completion

    client = ResilientGrokClient(api_key="test_key")
    result = client.chat_structured(
        model="grok-4.20-multi-agent-beta-0309",
        messages=[{"role": "user", "content": "test"}],
        response_model=MockAnalysis,
    )

    assert isinstance(result, MockAnalysis)
    assert result.metric == "token_count"
    assert result.value == 42
