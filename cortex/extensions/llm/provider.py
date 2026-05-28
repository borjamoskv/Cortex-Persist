# This file is part of CORTEX. Apache-2.0. Change Date: 2030-01-01.

"""Universal LLM Provider - OpenAI-compatible async client with intent routing."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import time
from typing import Any, Final

import httpx

from cortex.extensions.llm._audit import spectral_audit
from cortex.extensions.llm._backoff import handle_429_backoff
from cortex.extensions.llm._models import BaseProvider, CortexPrompt, IntentProfile
from cortex.extensions.llm._presets import get_prefix_cache_config, load_presets
from cortex.extensions.llm._result_cache import ResultCache
from cortex.extensions.llm._stealth import (
    apply_causal_jitter,
    prepare_stealth_headers,
    sanitize_response,
)
from cortex.extensions.llm.gemini_cache import get_gemini_gateway
from cortex.extensions.llm.quota import SovereignQuotaManager

__all__ = ["LLMProvider"]

logger = logging.getLogger("cortex.extensions.llm")

_CONTENT_TYPE_JSON: Final[str] = "application/json"
_QUOTA_MANAGER: SovereignQuotaManager | None = None
_RESULT_CACHE: ResultCache | None = None


def _get_quota_manager() -> SovereignQuotaManager:
    """Lazily create the shared quota manager to avoid import-time DB setup."""
    global _QUOTA_MANAGER
    if _QUOTA_MANAGER is None:
        _QUOTA_MANAGER = SovereignQuotaManager()
    return _QUOTA_MANAGER


def _get_result_cache() -> ResultCache:
    """Lazily create the shared result cache."""
    global _RESULT_CACHE
    if _RESULT_CACHE is None:
        _RESULT_CACHE = ResultCache()
    return _RESULT_CACHE


class LLMProvider(BaseProvider):
    """Universal OpenAI-compatible async LLM client.

    Works with ANY endpoint that speaks the OpenAI chat completions
    protocol. Use a preset name or 'custom' with explicit URL/key/model.

    Usage::

        provider = LLMProvider(provider="qwen")
        answer = await provider.complete("What is CORTEX?")
    """

    @classmethod
    def list_providers(cls) -> list[str]:
        """List names of supported LLM provider presets."""
        return sorted(list(load_presets().keys()))

    def __init__(
        self,
        provider: str = "qwen",
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        presets = load_presets()

        if provider == "custom":
            self._init_custom(api_key, model, base_url)
        elif provider in presets:
            self._init_preset(provider, presets[provider], api_key, model, base_url)
        else:
            supported = sorted(list(presets.keys()) + ["custom"])
            raise ValueError(f"Unknown LLM provider '{provider}'. Supported: {supported}")

        self._client = httpx.AsyncClient(timeout=60.0)
        self._semaphore = asyncio.Semaphore(100)
        logger.info(
            "LLM [READY] -> Provider: %s | Model: %s | URL: %s",
            self._provider,
            self._model,
            self._base_url,
        )

    def _init_custom(self, api_key: str | None, model: str | None, base_url: str | None) -> None:
        """Initialize a custom provider configuration."""
        self._provider = "custom"
        self._base_url = base_url or os.environ.get("CORTEX_LLM_BASE_URL")
        self._model = model or os.environ.get("CORTEX_LLM_MODEL", "gpt-4")
        self._api_key = api_key or os.environ.get("CORTEX_LLM_API_KEY")
        self._context_window = 128000
        self._extra_headers = {}
        self._intent_affinity: frozenset[IntentProfile] = frozenset({IntentProfile.GENERAL})
        self._intent_model_map: dict[IntentProfile, str] = {}
        self._tier = "high"
        self._cost_class = "medium"
        self._gemini_gateway = None

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
        self._context_window = preset.get("context_window", 128000)
        self._extra_headers = preset.get("extra_headers", {})
        self._api_key = api_key
        self._tier = preset.get("tier", "high")
        self._cost_class = preset.get("cost_class", "medium")
        self._gemini_gateway = None

        # Resolve intent affinity from preset specialization tags
        _TAG_MAP: dict[str, IntentProfile] = {
            "code": IntentProfile.CODE,
            "reasoning": IntentProfile.REASONING,
            "creative": IntentProfile.CREATIVE,
            "architect": IntentProfile.ARCHITECT,
            "general": IntentProfile.GENERAL,
        }
        raw_specs: list[str] = preset.get("specialization", ["general"])
        self._intent_affinity = frozenset(
            _TAG_MAP[t] for t in raw_specs if t in _TAG_MAP
        ) or frozenset({IntentProfile.GENERAL})

        # Intent-to-model map (optional)
        raw_map: dict[str, str] = preset.get("intent_model_map", {})
        self._intent_model_map = {
            _TAG_MAP[tag]: mid for tag, mid in raw_map.items() if tag in _TAG_MAP
        }

        # Resolve API key if not explicitly provided
        env_key = preset.get("env_key") or preset.get("api_key_env")
        if not self._api_key and env_key:
            self._api_key = os.environ.get(env_key)

        if not self._api_key and provider not in ["ollama", "lmstudio", "llamacpp", "vllm", "jan"]:
            raise ValueError(f"Provider '{provider}' requires API key ({env_key})")

    def _prepare_request(self) -> tuple[str, dict[str, str]]:
        url = f"{self._base_url.rstrip('/')}/chat/completions"  # pyright: ignore
        headers = prepare_stealth_headers(self._extra_headers)
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return url, headers

    async def complete(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        intent: IntentProfile = IntentProfile.GENERAL,
        prefix_cache_key: str | None = None,
    ) -> str:
        """Send a chat completion request. Returns the response text."""
        model_name = self._resolve_model(intent)
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Apply KV Prefix Cache Optimization (AX-042)
        cache_config = get_prefix_cache_config(self._provider)
        if cache_config.get("enabled") and prefix_cache_key and self._provider == "gemini":
            if not self._gemini_gateway:
                self._gemini_gateway = get_gemini_gateway(self._api_key or "")
            remote_cache = await self._gemini_gateway.get_or_create_cache(
                cache_key=prefix_cache_key,
                system_prompt=system,
                model=model_name.replace("models/", ""),
                ttl_seconds=cache_config.get("ttl_seconds", 3600),
            )
            if remote_cache:
                # Bypass OpenAI compatible endpoint altogether, fire native REST to save exergy
                return await self._execute_gemini_native(
                    prompt=prompt,
                    model_name=model_name,
                    remote_cache=remote_cache,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

        # Persistent Cache Check (Ω₂)
        cache = _get_result_cache()
        if cached := cache.get(payload):
            return cached

        await _get_quota_manager().acquire(tokens=1)
        url, headers = self._prepare_request()

        current_system = system
        response_text = ""

        # Phase 1: Shadow Re-phrasing (Ω₂₃)
        for attempt in range(5):
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": current_system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
            }
            if model_name.startswith(("o1", "o3")):
                payload["max_completion_tokens"] = max_tokens
                payload.pop("temperature", None)
            else:
                payload["max_tokens"] = max_tokens

            response_text = await self._execute_completion(url, headers, payload, wrap_errors=False)

            # Spectral Audit check
            if spectral_audit(response_text):
                cache.set(payload, response_text, provider=self._provider, model=model_name)
                return response_text

            if attempt < 4:
                logger.warning(
                    "Ω₂₃: Audit [FAIL] -> Attempting Shadow Re-phrasing (Try %d)", attempt + 2
                )
                # Use SHA256 for security compliance (AX-VII)
                noise = hashlib.sha256(f"{time.time()}-{attempt}".encode()).hexdigest()[:6]
                current_system = (
                    f"{system}\n\n[Sovereign-UUID: {noise}]\n"
                    "Mandato: Prohibida la prosa decorativa. Ejecuta directamente."
                )
                await apply_causal_jitter(tokens_estimate=50)

        cache.set(payload, response_text, provider=self._provider, model=model_name)
        return response_text

    async def _execute_gemini_native(
        self, prompt: str, model_name: str, remote_cache: str, temperature: float, max_tokens: int
    ) -> str:
        """Execute inference against Gemini's native API bypassing the OpenAI compatibility logic.
        Required because OpenAI compatibility endpoints do not support cachedContents mapping yet.
        """
        await _get_quota_manager().acquire(tokens=1)
        model_stripped = model_name.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_stripped}:generateContent?key={self._api_key}"

        headers = {"Content-Type": "application/json"}
        payload = {
            "cachedContent": remote_cache,
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }

        # O1/O3 handling skip, Gemini needs standard generation config
        payload["generationConfig"] = {"temperature": temperature, "maxOutputTokens": max_tokens}

        await apply_causal_jitter(tokens_estimate=50)
        async with self._semaphore:
            response = await self._client.post(url, headers=headers, json=payload)

        try:
            response.raise_for_status()
            data = response.json()
            raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
            return sanitize_response(raw_content)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return await handle_429_backoff(self, url, headers, payload, e)
            logger.error("Native Gemini API Failure: %s", e.response.text[:500])
            raise ValueError(f"HTTP {e.response.status_code} from native Gemini") from e

    async def _execute_completion(
        self, url: str, headers: dict[str, str], payload: dict[str, Any], wrap_errors: bool
    ) -> str:
        try:
            return await self._execute_completion_raw(url, headers, payload)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return await handle_429_backoff(self, url, headers, payload, e)

            logger.error(
                "LLM API Failure [%s %s]: %s",
                e.response.status_code,
                self._provider,
                e.response.text[:500],
            )
            if wrap_errors:
                from cortex.utils.errors import CortexError

                raise CortexError(f"HTTP {e.response.status_code} from {self._provider}") from e
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
        await apply_causal_jitter(tokens_estimate=len(payload.get("messages", [])) * 50)
        async with self._semaphore:
            response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        self._log_resolved_model(payload, data)
        raw_content = data["choices"][0]["message"]["content"]
        return sanitize_response(raw_content)

    def _log_resolved_model(self, payload: dict[str, Any], response_data: dict[str, Any]) -> None:
        """Log when a meta-router resolves to a different model than requested."""
        requested = payload.get("model", "")
        actual = response_data.get("model", requested)
        if actual and actual != requested:
            logger.info(
                "LLM [%s] meta-routed: requested=%s → resolved=%s",
                self._provider,
                requested,
                actual,
            )

    async def stream(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        intent: IntentProfile = IntentProfile.GENERAL,
    ):
        """Stream a chat completion request. Yields text chunks."""
        await _get_quota_manager().acquire(tokens=1)
        url, headers = self._prepare_request()

        # Apply Stealth Mode headers
        headers = prepare_stealth_headers(headers)

        model_name = self._resolve_model(intent)
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "stream": True,
        }
        if model_name.startswith(("o1", "o3")):
            payload["max_completion_tokens"] = max_tokens
            payload.pop("temperature", None)
        else:
            payload["max_tokens"] = max_tokens

        try:
            async with self._semaphore:
                async with self._client.stream(
                    "POST", url, headers=headers, json=payload
                ) as response:
                    response.raise_for_status()
                    async for chunk in self._process_stream_lines(response):
                        yield chunk
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Fallback non-streaming call if throttled during stream start
                # or handle backoff for the remaining stream (complex, using sequential for now)
                logger.warning(
                    "LLM Stream [429 Quota Exceeded] -> Falling back to resilient execution."
                )
                result = await handle_429_backoff(self, url, headers, payload, e)
                yield result
                return

            logger.error(
                "LLM Stream Failure [%s]: %s",
                self._provider,
                e.response.text[:500],
            )
            raise

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

    def _resolve_model(self, intent: IntentProfile) -> str:
        """Return the optimal model for the given intent."""
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
        model_name = self._resolve_model(prompt.intent)
        messages = prompt.to_openai_messages()

        # Stealth / Causal logic (Ω₂₃)
        if getattr(prompt, "stealth", False) and messages:
            noise_id = hashlib.sha256(f"{time.time()}{random.random()}".encode()).hexdigest()[:8]

            # Find last user message, preserving system prompt (KV cache) purity
            for msg in reversed(messages):
                if msg["role"] == "user":
                    msg["content"] += f"\n\n<!-- ctx:{noise_id} -->"
                    msg["content"] = (" " * random.randint(0, 2)) + msg["content"]
                    break

            await apply_causal_jitter(tokens_estimate=50)

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": prompt.temperature,
        }

        # Apply KV Prefix Cache Optimization (AX-042)
        cache_config = get_prefix_cache_config(self._provider)
        prefix_cache_key = getattr(prompt, "prefix_cache_key", None)
        system_extraction = ""
        if messages and messages[0]["role"] == "system":
            system_extraction = messages[0]["content"]

        if cache_config.get("enabled") and prefix_cache_key and self._provider == "gemini":
            if not self._gemini_gateway:
                self._gemini_gateway = get_gemini_gateway(self._api_key or "")
            remote_cache = await self._gemini_gateway.get_or_create_cache(
                cache_key=prefix_cache_key,
                system_prompt=system_extraction,
                model=model_name.replace("models/", ""),
                ttl_seconds=cache_config.get("ttl_seconds", 3600),
            )
            if remote_cache:
                # Find the user prompt (assumes single shot or joins string)
                user_msg = " ".join([m["content"] for m in messages if m["role"] == "user"])
                return await self._execute_gemini_native(
                    prompt=user_msg,
                    model_name=model_name,
                    remote_cache=remote_cache,
                    temperature=prompt.temperature,
                    max_tokens=prompt.max_tokens,
                )

        # Persistent Cache Check (Ω₂)
        cache = _get_result_cache()
        if cached := cache.get(payload):
            return cached

        await _get_quota_manager().acquire(tokens=1)
        url, headers = self._prepare_request()

        # Stealth Mode
        headers = prepare_stealth_headers(headers)

        if model_name.startswith(("o1", "o3")):
            payload["max_completion_tokens"] = prompt.max_tokens
            payload.pop("temperature", None)
        else:
            payload["max_tokens"] = prompt.max_tokens

        result = await self._execute_completion(url, headers, payload, wrap_errors=True)
        cache.set(payload, result, provider=self._provider, model=model_name)
        return result

    @property
    def model_name(self) -> str:
        """Active model name (BaseProvider contract)."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Provider identifier (BaseProvider contract)."""
        return self._provider

    @property
    def intent_affinity(self) -> frozenset[IntentProfile]:
        """Intenciones para las que este provider es óptimo."""
        return self._intent_affinity

    @property
    def tier(self) -> str:
        """Provider tier from preset."""
        return self._tier

    @property
    def cost_class(self) -> str:
        """Cost class from preset."""
        return self._cost_class

    @property
    def context_window(self) -> int:
        """Context window in tokens."""
        return self._context_window

    async def close(self) -> None:
        """Gracefully close the HTTP client."""
        await self._client.aclose()

    def get_intent_models(self) -> dict[str, str]:
        """Return the intent-to-model mapping."""
        return {k.value: v for k, v in self._intent_model_map.items()}

    def __repr__(self) -> str:
        if self._intent_model_map:
            models = ", ".join(f"{k.value}={v}" for k, v in self._intent_model_map.items())
            return f"LLMProvider(provider={self._provider!r}, models=[{models}])"
        return f"LLMProvider(provider={self._provider!r}, model={self._model!r})"
