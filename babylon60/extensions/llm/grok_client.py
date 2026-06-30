# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.

"""Grok Resilient Client.

Provides a robust, resilient client wrapper for xAI Grok models
(specifically grok-4.20-multi-agent-beta-0309) with conversation history
management, JSON structured outputs, and rate-limit retry logic.
"""

from __future__ import annotations

import logging
import os
from typing import Any, AsyncIterator, Iterator, Type, TypeVar

import openai
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ConversationHistory:
    """Manages chat messages history with a sliding window constraint.

    Preserves the system prompt at index 0 and prunes older messages
    when exceeding max_messages limit.
    """

    def __init__(self, system_prompt: str | None = None, max_messages: int = 40) -> None:
        self.max_messages = max_messages
        self.messages: list[dict[str, str]] = []
        if system_prompt:
            self.set_system_prompt(system_prompt)

    def set_system_prompt(self, system_prompt: str) -> None:
        """Sets or replaces the initial system prompt."""
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = system_prompt
        else:
            self.messages.insert(0, {"role": "system", "content": system_prompt})

    def add_message(self, role: str, content: str) -> None:
        """Appends a new message and prunes older messages if threshold is reached."""
        self.messages.append({"role": role, "content": content})
        self._prune()

    def _prune(self) -> None:
        """Prunes history while keeping the system prompt intact."""
        if len(self.messages) <= self.max_messages:
            return

        has_system = self.messages and self.messages[0]["role"] == "system"
        start_idx = 1 if has_system else 0

        # Calculate how many to remove
        to_remove = len(self.messages) - self.max_messages
        
        # Remove oldest non-system messages
        for _ in range(to_remove):
            if len(self.messages) > start_idx:
                self.messages.pop(start_idx)

    def clear(self) -> None:
        """Clears messages history, preserving system prompt if set."""
        has_system = self.messages and self.messages[0]["role"] == "system"
        system_msg = self.messages[0] if has_system else None
        self.messages.clear()
        if system_msg:
            self.messages.append(system_msg)

    def get_messages(self) -> list[dict[str, str]]:
        """Returns the messages formatted for OpenAI client."""
        return self.messages.copy()


class ResilientGrokClient:
    """A resilient wrapper client for the xAI Grok API.

    Implements automatic exponential backoff retry for rate limits (429)
    and network connection timeouts/failures. Supports synchronous,
    asynchronous, streaming, and Pydantic structured output interactions.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.x.ai/v1",
        timeout: float = 60.0,
    ) -> None:
        # Load from environment fallback
        self.api_key = api_key or os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
        if not self.api_key:
            logger.warning("No XAI_API_KEY or GROK_API_KEY found in environment variables.")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Initialize clients lazily to prevent env verification errors at load-time
        self._sync_client: OpenAI | None = None
        self._async_client: AsyncOpenAI | None = None

    @property
    def sync_client(self) -> OpenAI:
        """Lazy initializer for the synchronous OpenAI client."""
        if self._sync_client is None:
            self._sync_client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._sync_client

    @property
    def async_client(self) -> AsyncOpenAI:
        """Lazy initializer for the asynchronous OpenAI client."""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._async_client

    @retry(
        retry=retry_if_exception_type((
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.RateLimitError,
        )),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        """Synchronously request completion with retry policy."""
        try:
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            completion = self.sync_client.chat.completions.create(**payload)
            content = completion.choices[0].message.content
            return content or ""
        except openai.APIError as e:
            logger.error("xAI API call failed: %s", e)
            raise

    @retry(
        retry=retry_if_exception_type((
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.RateLimitError,
        )),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Synchronously request streaming completion with retry policy."""
        try:
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            response_stream = self.sync_client.chat.completions.create(**payload)
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.APIError as e:
            logger.error("xAI API streaming call failed: %s", e)
            raise

    @retry(
        retry=retry_if_exception_type((
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.RateLimitError,
        )),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def chat_structured(
        self,
        model: str,
        messages: list[dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> T:
        """Synchronously request parsed Pydantic structured output with retry policy."""
        try:
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "response_format": response_model,
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            # Uses OpenAI Beta parse helper
            completion = self.sync_client.beta.chat.completions.parse(**payload)
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                raise ValueError("Failed to parse response into Pydantic model.")
            return parsed
        except (openai.APIError, ValueError) as e:
            logger.error("xAI API structured call failed: %s", e)
            raise

    # ─── Async Implementations ───────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type((
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.RateLimitError,
        )),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def chat_async(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        """Asynchronously request completion with retry policy."""
        try:
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            completion = await self.async_client.chat.completions.create(**payload)
            content = completion.choices[0].message.content
            return content or ""
        except openai.APIError as e:
            logger.error("xAI API async call failed: %s", e)
            raise

    @retry(
        retry=retry_if_exception_type((
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.RateLimitError,
        )),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def chat_stream_async(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Asynchronously request streaming completion with retry policy."""
        try:
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            response_stream = await self.async_client.chat.completions.create(**payload)
            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.APIError as e:
            logger.error("xAI API async streaming call failed: %s", e)
            raise

    @retry(
        retry=retry_if_exception_type((
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.RateLimitError,
        )),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def chat_structured_async(
        self,
        model: str,
        messages: list[dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> T:
        """Asynchronously request parsed Pydantic structured output with retry policy."""
        try:
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "response_format": response_model,
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            completion = await self.async_client.beta.chat.completions.parse(**payload)
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                raise ValueError("Failed to parse response into Pydantic model.")
            return parsed
        except (openai.APIError, ValueError) as e:
            logger.error("xAI API async structured call failed: %s", e)
            raise
