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
from typing import Any, Final

import httpx

logger = logging.getLogger("cortex.llm")

# ─── Configuration & Presets ──────────────────────────────────────────

_ASSET_PATH: Final[str] = os.path.join(
    os.path.dirname(__file__), "..", "assets", "llm_presets.json"
)

# Global cache for presets to avoid redundant I/O
_PRESETS_CACHE: dict[str, dict[str, Any]] = {}


def _load_presets() -> dict[str, dict[str, Any]]:
    """Lazy-load provider presets from assets with error recovery."""
    global _PRESETS_CACHE
    if not _PRESETS_CACHE:
        try:
            # Handle absolute path for robustness
            path = os.path.abspath(_ASSET_PATH)
            if not os.path.exists(path):
                logger.error("Sovereign Failure: LLM presets missing at %s", path)
                return {}

            with open(path, encoding="utf-8") as f:
                _PRESETS_CACHE = json.load(f)
                logger.debug("LLM: Loaded %d presets from assets", len(_PRESETS_CACHE))
        except (json.JSONDecodeError, OSError) as exc:
            logger.critical("LLM: Failed to load presets: %s", exc)
            return {}
    return _PRESETS_CACHE


# ─── Implementation ───────────────────────────────────────────────────


class LLMProvider:
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

        # ── Custom endpoint: user provides everything ──────────────
        if provider == "custom":
            self._provider = "custom"
            self._base_url = base_url or os.environ.get("CORTEX_LLM_BASE_URL", "")
            self._model = model or os.environ.get("CORTEX_LLM_MODEL", "custom-model")
            self._api_key = api_key or os.environ.get("CORTEX_LLM_API_KEY", "")
            self._context_window = 32768
            self._extra_headers: dict[str, str] = {}

            if not self._base_url:
                raise ValueError(
                    "Custom provider requires CORTEX_LLM_BASE_URL or base_url parameter."
                )

        # ── Preset endpoint ────────────────────────────────────────
        elif provider in presets:
            config = presets[provider]
            self._provider = provider
            self._base_url = base_url or config["base_url"]
            self._model = model or os.environ.get("CORTEX_LLM_MODEL", "") or config["default_model"]
            self._context_window = config["context_window"]
            self._extra_headers = config.get("extra_headers", {})

            # Resolve API key
            env_key = config.get("env_key")
            if env_key:
                self._api_key = api_key or os.environ.get(env_key, "")
                if not self._api_key:
                    raise ValueError(
                        f"Environment variable '{env_key}' is required for provider '{provider}'."
                    )
            else:
                self._api_key = api_key or ""

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

    async def complete(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat completion request. Returns the response text."""
        url = f"{self._base_url.rstrip('/')}/chat/completions"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            **self._extra_headers,
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

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
