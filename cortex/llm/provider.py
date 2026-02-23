# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.0 — Universal LLM Provider (OpenAI-compatible).

Sovereign-grade async client for ANY OpenAI-compatible LLM endpoint.
Modularized architecture with externalized presets and high-precision logging.

Environment:
    CORTEX_LLM_PROVIDER=qwen       (preset name, or 'custom')
    CORTEX_LLM_MODEL=override      (optional model override)
    CORTEX_LLM_BASE_URL=https://.. (required if provider='custom')
    CORTEX_LLM_API_KEY=your-key    (required if provider='custom')
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Final

import httpx

from cortex.llm.router import BaseProvider, CortexPrompt

__all__ = ["LLMProvider"]

logger = logging.getLogger("cortex.llm")

# ─── Configuration & Presets ──────────────────────────────────────────

_ASSET_PATH: Final[str] = str(Path(__file__).parent.parent / "assets" / "llm_presets.json")
_CONTENT_TYPE_JSON: Final[str] = "application/json"

# Global cache for presets to avoid redundant I/O
_PRESETS_CACHE: dict[str, dict[str, Any]] = {}


def _load_presets() -> dict[str, dict[str, Any]]:
    """Lazy-load provider presets from assets with error recovery."""
    global _PRESETS_CACHE
    if not _PRESETS_CACHE:
        try:
            # Handle absolute path for robustness
            path = Path(_ASSET_PATH).resolve()
            if not path.exists():
                logger.error("Sovereign Failure: LLM presets missing at %s", path)
                return {}

            with path.open(encoding="utf-8") as f:
                _PRESETS_CACHE = json.load(f)
                logger.debug("LLM: Loaded %d presets from assets", len(_PRESETS_CACHE))
        except (json.JSONDecodeError, OSError) as exc:
            logger.critical("LLM: Failed to load presets: %s", exc)
            return {}
    return _PRESETS_CACHE


# ─── Implementation ───────────────────────────────────────────────────


class LLMProvider(BaseProvider):
    """Universal OpenAI-compatible async LLM client.

    Works with ANY endpoint that speaks the OpenAI chat completions
    protocol. Use a preset name or 'custom' with explicit URL/key/model.

    Usage::

        provider = LLMProvider(provider="qwen")
        answer = await provider.complete("What is CORTEX?")
    """

    def __init__(
        self,
        provider: str = "qwen",
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        presets = _load_presets()

        if provider == "custom":
            self._init_custom(api_key, model, base_url)
        elif provider in presets:
            self._init_preset(provider, presets[provider], api_key, model, base_url)

        else:
            supported = sorted(list(presets.keys()) + ["custom"])
            raise ValueError(f"Unknown LLM provider '{provider}'. Supported: {supported}")

        self._client = httpx.AsyncClient(timeout=60.0)
        logger.info(
            "LLM [READY] -> Provider: %s | Model: %s | URL: %s",
            self._provider,
            self._model,
            self._base_url,
        )

    def _init_custom(
        self,
        api_key: str | None,
        model: str | None,
        base_url: str | None,
    ) -> None:
        """Initialize a custom provider configuration."""
        self._provider = "custom"
        self._base_url = base_url or os.environ.get("CORTEX_LLM_BASE_URL")
        self._model = model or os.environ.get("CORTEX_LLM_MODEL", "gpt-4")
        self._api_key = api_key or os.environ.get("CORTEX_LLM_API_KEY")
        self._context_window = 128000
        self._extra_headers = {}

        if not self._base_url:
            raise ValueError("Custom LLM provider requires CORTEX_LLM_BASE_URL")

    def _init_preset(
        self,
        provider: str,
        preset: dict[str, Any],
        api_key: str | None,
        model: str | None,
        base_url: str | None,
    ) -> None:
        """Initialize from a known provider preset."""
        self._provider = provider
        self._base_url = base_url or preset["base_url"]
        self._model = model or os.environ.get("CORTEX_LLM_MODEL") or preset["default_model"]
        self._context_window = preset["context_window"]
        self._extra_headers = preset.get("extra_headers", {})
        self._api_key = api_key

        # Resolve API key if not explicitly provided
        env_key = preset.get("env_key") or preset.get("api_key_env")
        if not self._api_key and env_key:
            self._api_key = os.environ.get(env_key)

        if not self._api_key:
            # Some providers like Ollama don't need keys
            if provider not in ["ollama", "lmstudio", "llamacpp", "vllm", "jan"]:
                msg = f"LLM provider '{provider}' requires an API key "
                msg += f"(api_key argument or {env_key} env var)"
                raise ValueError(msg)


    def _prepare_request(self) -> tuple[str, dict[str, str]]:
        url = f"{self._base_url.rstrip('/')}/chat/completions"
        headers: dict[str, str] = {
            "Content-Type": _CONTENT_TYPE_JSON,
            **self._extra_headers,
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return url, headers

    async def complete(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat completion request. Returns the response text."""
        url, headers = self._prepare_request()

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(
                "LLM API Failure [%s %s]: %s",
                e.response.status_code,
                self._provider,
                e.response.text[:500],
            )
            raise
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error("LLM Parse Error [%s]: %s", self._provider, e)
            raise ValueError(f"Unexpected response format from {self._provider}") from e

    async def _process_stream_lines(self, response: httpx.Response):
        """Consume and parse SSE lines from an active HTTP stream."""
        async for line in response.aiter_lines():
            if not line or not line.startswith("data: "):
                continue

            data_str = line[6:].strip()
            if data_str == "[DONE]":
                break

            try:
                data = json.loads(data_str)
                if delta := data["choices"][0].get("delta", {}).get("content"):
                    yield delta
            except (json.JSONDecodeError, KeyError, IndexError):
                continue

    async def stream(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ):
        """Stream a chat completion request. Yields text chunks."""
        url, headers = self._prepare_request()

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with self._client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for chunk in self._process_stream_lines(response):
                    yield chunk
        except httpx.HTTPStatusError as e:
            logger.error("LLM Stream Failure [%s]: %s", self._provider, e.response.text[:500])
            raise

    async def invoke(self, prompt: CortexPrompt) -> str:
        """Traduce el CortexPrompt al formato nativo del LLM y ejecuta la inferencia."""
        url, headers = self._prepare_request()

        payload = {
            "model": self._model,
            "messages": prompt.to_openai_messages(),
            "temperature": prompt.temperature,
            "max_tokens": prompt.max_tokens,
        }

        try:
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(
                "LLM API Failure [%s %s]: %s",
                e.response.status_code,
                self._provider,
                e.response.text[:500],
            )
            from cortex.errors import CortexError

            raise CortexError(f"HTTP {e.response.status_code} from {self._provider}") from e
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error("LLM Parse Error [%s]: %s", self._provider, e)
            from cortex.errors import CortexError

            raise CortexError(f"Unexpected JSON format from {self._provider}") from e

    @property
    def model_name(self) -> str:
        """Active model name."""
        return self._model

    @property
    def model(self) -> str:
        """Active model name."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return self._provider

    @property
    def context_window(self) -> int:
        """Context window in tokens."""
        return self._context_window

    async def close(self) -> None:
        """Gracefully close the HTTP client."""
        await self._client.aclose()

    def __repr__(self) -> str:
        return f"LLMProvider(provider={self._provider!r}, model={self._model!r})"

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return all available preset provider names + 'custom'."""
        presets = _load_presets()
        return sorted(list(presets.keys()) + ["custom"])

    @classmethod
    def get_preset_info(cls, provider: str) -> dict[str, Any] | None:
        """Return preset config for a provider, or None if not found."""
        return _load_presets().get(provider)
