# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.2 — Universal LLM Provider (OpenAI-compatible).

Sovereign-grade async client for ANY OpenAI-compatible LLM endpoint.
Modularized architecture with externalized presets, high-precision logging,
and intent-aware model routing via ``intent_model_map``.

Intent Model Map
~~~~~~~~~~~~~~~~
Providers that serve multiple models (OpenRouter, Groq, Together, Fireworks,
DeepInfra) declare an ``intent_model_map`` in their preset (llm_presets.json).
This maps each ``IntentProfile`` to the optimal model available on that
provider, enabling deterministic per-intent routing without code changes.

Environment:
    CORTEX_LLM_PROVIDER=qwen       (preset name, or 'custom')
    CORTEX_LLM_MODEL=override      (optional model override)
    CORTEX_LLM_BASE_URL=https://.. (required if provider='custom')
    CORTEX_LLM_API_KEY=your-key    (required if provider='custom')
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Final

from curl_cffi.requests import AsyncSession, RequestsError

from cortex.concurrency import Singleflight, SovereignGate
from cortex.llm.quota import SovereignQuotaManager
from cortex.llm.router import BaseProvider, CortexPrompt, IntentProfile

__all__ = ["LLMProvider"]

logger = logging.getLogger("cortex.llm")

# ─── Configuration & Presets ──────────────────────────────────────────

_ASSET_PATH: Final[str] = str(Path(__file__).parent.parent.parent / "config" / "llm_presets.json")
_CONTENT_TYPE_JSON: Final[str] = "application/json"

# Global cache for presets to avoid redundant I/O
_PRESETS_CACHE: dict[str, dict[str, Any]] = {}

_QUOTA_MANAGER = SovereignQuotaManager()
_SINGLEFLIGHT = Singleflight()
_GATE = SovereignGate.shared()


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
        impersonate: str = "chrome120",
    ):
        presets = _load_presets()

        if provider == "custom":
            self._init_custom(api_key, model, base_url)
        elif provider in presets:
            self._init_preset(provider, presets[provider], api_key, model, base_url)

        else:
            supported = sorted(list(presets.keys()) + ["custom"])
            raise ValueError(f"Unknown LLM provider '{provider}'. Supported: {supported}")

        self._client = AsyncSession(impersonate=impersonate, timeout=60.0)
        # Sovereign Gate is now global singleton via _GATE
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
        self._intent_affinity: frozenset[IntentProfile] = frozenset({IntentProfile.GENERAL})
        self._intent_model_map: dict[IntentProfile, str] = {}  # no map for custom

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

        # Resolve intent affinity from preset specialization tags
        _TAG_MAP: dict[str, IntentProfile] = {
            "code": IntentProfile.CODE,
            "reasoning": IntentProfile.REASONING,
            "creative": IntentProfile.CREATIVE,
            "architect": IntentProfile.ARCHITECT,
            "general": IntentProfile.GENERAL,
        }
        raw_specs: list[str] = preset.get("specialization", ["general"])
        self._intent_affinity: frozenset[IntentProfile] = frozenset(
            _TAG_MAP[tag] for tag in raw_specs if tag in _TAG_MAP
        ) or frozenset({IntentProfile.GENERAL})

        # Intent-to-model map (optional) — permite que un provider como OpenRouter
        # use modelos especializados según la intención del prompt.
        raw_map: dict[str, str] = preset.get("intent_model_map", {})
        self._intent_model_map: dict[IntentProfile, str] = {
            _TAG_MAP[tag]: model_id for tag, model_id in raw_map.items() if tag in _TAG_MAP
        }
        if self._intent_model_map:
            logger.debug(
                "LLM [%s] intent_model_map loaded: %s",
                provider,
                {k.value: v for k, v in self._intent_model_map.items()},
            )

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
        # type: ignore[reportOptionalMemberAccess]
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
        intent: IntentProfile = IntentProfile.GENERAL,
    ) -> str:
        """Send a chat completion request. Returns the response text.

        Args:
            intent: Intent profile for model selection. When the provider has an
                ``intent_model_map``, this selects the optimal model for the task.
        """
        # Quota/Semaphore handled by SovereignGate in _execute_completion_raw
        url, headers = self._prepare_request()

        payload = {
            "model": self._resolve_model(intent),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        return await self._execute_completion(url, headers, payload, wrap_errors=False)

    async def _execute_completion(
        self, url: str, headers: dict[str, str], payload: dict[str, Any], wrap_errors: bool
    ) -> str:
        import hashlib

        # Request Coalescing (Defecto #3)
        # Hash based on model, messages, and temperature to collapse identical calls
        call_key = hashlib.sha256(
            json.dumps({"url": url, "payload": payload}, sort_keys=True).encode()
        ).hexdigest()

        try:
            return await _SINGLEFLIGHT.do(
                call_key,
                lambda: self._execute_completion_raw(url, headers, payload)
            )
        except RequestsError as e:
            if e.response is not None and e.response.status_code == 429:
                return await self._handle_429_backoff(url, headers, payload, e)

            status_code = e.response.status_code if e.response else "???"
            resp_text = e.response.text[:500] if e.response else str(e)
            logger.error(
                "LLM API Failure [%s %s]: %s",
                status_code,
                self._provider,
                resp_text,
            )
            if wrap_errors:
                from cortex.utils.errors import CortexError

                raise CortexError(f"HTTP {status_code} from {self._provider}") from e
            raise
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error("LLM Parse Error [%s]: %s", self._provider, e)
            if wrap_errors:
                from cortex.utils.errors import CortexError

                raise CortexError(f"Unexpected JSON format from {self._provider}") from e
            raise ValueError(f"Unexpected response format from {self._provider}") from e

    async def _execute_completion_raw(
        self, url: str, headers: dict[str, str], payload: dict[str, Any]
    ) -> str:
        """Executes a single completion attempt directly. Throws native exceptions."""
        async with _GATE.gate(provider=self._provider):
            response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        self._log_resolved_model(payload, data)
        return data["choices"][0]["message"]["content"]

    def _log_resolved_model(self, payload: dict[str, Any], response_data: dict[str, Any]) -> None:
        """Log when a meta-router resolves to a different model than requested.

        Enables traceability for hierarchical routing — when CORTEX
        requests 'openrouter/auto' and OpenRouter resolves to e.g.
        'anthropic/claude-3.5-sonnet', this captures both layers.
        """
        requested = payload.get("model", "")
        actual = response_data.get("model", requested)
        if actual and actual != requested:
            logger.info(
                "LLM [%s] meta-routed: requested=%s → resolved=%s",
                self._provider,
                requested,
                actual,
            )

    def _extract_retry_delay(self, text: str) -> float | None:
        """Extrae el delay de reintento desde el JSON o via regex."""
        try:
            data = json.loads(text)
            for detail in data.get("error", {}).get("details", []):
                meta = detail.get("metadata", {})
                delay_str = detail.get("retryDelay") or meta.get("quotaResetDelay")
                if delay_str and isinstance(delay_str, str):
                    if delay_str.endswith("ms"):
                        return float(delay_str[:-2]) / 1000.0
                    elif delay_str.endswith("s"):
                        return float(delay_str[:-1])
        except (KeyError, TypeError, ValueError, AttributeError):
            pass

        match = re.search(r'"(?:quotaResetDelay|retryDelay)"\s*:\s*"([0-9\.]+)(m?s)"', text)
        if match:
            try:
                val = float(match.group(1))
                return val / 1000.0 if match.group(2) == "ms" else val
            except ValueError:
                pass

        return None

    async def _handle_429_backoff(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        original_error: RequestsError,
    ) -> str:
        """Maneja el backoff exponencial y reintentos para errores 429."""
        last_error = original_error
        for attempt in range(1, 4):
            resp_text = last_error.response.text if last_error.response else "{}"
            delay = self._extract_retry_delay(resp_text)

            # Singularidad de Vaciado en PULMONES (Drenaje para evadir el herd)
            if attempt == 1:
                _QUOTA_MANAGER.bankrupt(self._provider, penalty_seconds=delay or 5.0)

            # Hardware Entropy + Golden Ratio Asymmetric Jitter
            import secrets

            rng = secrets.SystemRandom()
            safe_delay = max(delay or 2.0, 2.0) * attempt + 1.0 + rng.uniform(0.1, 1.618**attempt)

            logger.warning(
                "LLM API [429 Quota Exceeded] on %s. Auto-sleeping for %.2fs (attempt %d/3)...",
                self._model,
                safe_delay,
                attempt,
            )
            await asyncio.sleep(safe_delay)

            try:
                return await self._execute_completion_raw(url, headers, payload)
            except RequestsError as e2:
                if e2.response is not None and e2.response.status_code == 429:
                    last_error = e2
                    continue
                raise original_error from e2
            except (ValueError, KeyError) as retry_e:
                logger.error("LLM Quota Retry Failure: %s", retry_e)
                raise original_error from retry_e

        return await self._execute_fallback(payload, last_error)

    async def _execute_fallback(
        self, payload: dict[str, Any], original_error: RequestsError
    ) -> str:
        """Ejecuta el fallback hacia un modelo más estable si todo falla."""
        logger.warning(
            "LLM API [429 Quota Exceeded Final] on %s. Fallback to Open Code (Qwen Coder)...",
            self._model,
        )

        if self._provider == "qwen":
            raise original_error

        fallback_provider = LLMProvider(provider="qwen")
        try:
            fb_url, fb_headers = fallback_provider._prepare_request()
            fb_payload = {
                "model": fallback_provider._model,
                "messages": payload.get("messages", []),
                "temperature": payload.get("temperature", 0.3),
                "max_tokens": payload.get("max_tokens", 2048),
            }
            return await fallback_provider._execute_completion_raw(fb_url, fb_headers, fb_payload)
        except (RequestsError, ValueError, KeyError) as fallback_e:
            logger.error("LLM Fallback Failure: %s", fallback_e)
            raise original_error from fallback_e
        finally:
            await fallback_provider.close()

    async def _process_stream_lines(self, response: Any):
        """Consume and parse SSE lines from an active HTTP stream."""
        # curl_cffi doesn't have aiter_lines(), it has iter_lines() (blocking) or we can use response.content
        # Better: use response.iter_lines() if it's async-compatible or wait...
        # curl_cffi AsyncSession stream returns an object that we can iterate over.
        async for line in response.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue

            data_str = line[6:].decode("utf-8").strip()
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
        intent: IntentProfile = IntentProfile.GENERAL,
    ):
        """Stream a chat completion request. Yields text chunks."""
        url, headers = self._prepare_request()

        payload = {
            "model": self._resolve_model(intent),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with _GATE.gate(provider=self._provider):
                # curl_cffi AsyncSession.post(..., stream=True) returns a context manager
                async with self._client.post(
                    url,
                    headers=headers,
                    json=payload,
                    stream=True,
                ) as response:
                    response.raise_for_status()
                    async for chunk in self._process_stream_lines(response):
                        yield chunk
        except RequestsError as e:
            resp_text = e.response.text[:500] if e.response else str(e)
            logger.error(
                "LLM Stream Failure [%s]: %s",
                self._provider,
                resp_text,
            )
            raise

    def _resolve_model(self, intent: IntentProfile) -> str:
        """Return the optimal model for the given intent.

        Uses ``intent_model_map`` when available (two-layer routing).
        Falls back to ``self._model`` for providers without a map.
        """
        if self._intent_model_map:
            resolved = self._intent_model_map.get(intent, self._model)
            if resolved != self._model:
                logger.debug(
                    "LLM [%s] intent=%s → model: %s",
                    self._provider,
                    intent.value,
                    resolved,
                )
            return resolved
        return self._model

    async def invoke(self, prompt: CortexPrompt) -> str:
        """Traduce el CortexPrompt al formato nativo del LLM y ejecuta la inferencia."""
        await _QUOTA_MANAGER.acquire(provider=self._provider, tokens=1)
        url, headers = self._prepare_request()

        payload = {
            "model": self._resolve_model(prompt.intent),
            "messages": prompt.to_openai_messages(),
            "temperature": prompt.temperature,
            "max_tokens": prompt.max_tokens,
        }

        return await self._execute_completion(url, headers, payload, wrap_errors=True)

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
    def intent_affinity(self) -> frozenset[IntentProfile]:
        """Intenciones para las que este provider es óptimo (leído del preset)."""
        return self._intent_affinity

    @property
    def context_window(self) -> int:
        """Context window in tokens."""
        return self._context_window

    async def close(self) -> None:
        """Gracefully close the HTTP client."""
        await self._client.aclose()

    def get_intent_models(self) -> dict[str, str]:
        """Return the intent-to-model mapping, or empty dict if none.

        Useful for introspection, CLIs, and dashboards.
        """
        return {k.value: v for k, v in self._intent_model_map.items()}

    @property
    def has_intent_routing(self) -> bool:
        """True if this provider routes different intents to different models."""
        return bool(self._intent_model_map)

    def __repr__(self) -> str:
        if self._intent_model_map:
            models = ", ".join(f"{k.value}={v}" for k, v in self._intent_model_map.items())
            return f"LLMProvider(provider={self._provider!r}, models=[{models}])"
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
