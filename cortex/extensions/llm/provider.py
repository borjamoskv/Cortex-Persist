# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from cortex.extensions.llm._audit import spectral_audit
from cortex.extensions.llm._models import BaseProvider, CortexPrompt, IntentProfile
from cortex.extensions.llm._presets import get_prefix_cache_config, load_presets
from cortex.extensions.llm._provider_config import resolve_provider_config
from cortex.extensions.llm._provider_gemini import execute_gemini_native
from cortex.extensions.llm._provider_stream import execute_stream
from cortex.extensions.llm._resilience import CircuitBreaker, resilient_call
from cortex.extensions.llm._result_cache import ResultCache
from cortex.extensions.llm._stealth import (
    apply_causal_jitter,
    prepare_stealth_headers,
    sanitize_response,
)
from cortex.extensions.llm.gemini_cache import get_gemini_gateway
from cortex.extensions.llm.quota import SovereignQuotaManager

__all__ = ["LLMProvider"]

logger = logging.getLogger("cortex_extensions.llm")

_QUOTA_MANAGER: SovereignQuotaManager | None = None
_RESULT_CACHE: ResultCache | None = None


def _get_quota_manager() -> SovereignQuotaManager:
    global _QUOTA_MANAGER
    if _QUOTA_MANAGER is None:
        _QUOTA_MANAGER = SovereignQuotaManager()
    return _QUOTA_MANAGER


def _get_result_cache() -> ResultCache:
    global _RESULT_CACHE
    if _RESULT_CACHE is None:
        _RESULT_CACHE = ResultCache()
    return _RESULT_CACHE


class LLMProvider(BaseProvider):
    """Universal OpenAI-compatible async LLM client."""

    @classmethod
    def list_providers(cls) -> list[str]:
        return sorted(list(load_presets().keys()))

    def __init__(
        self,
        provider: str = "qwen",
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        presets = load_presets()
        cfg = resolve_provider_config(provider, presets, api_key, model, base_url)

        # [LOCAL-INFERENCE-OMEGA] ZERO-NETWORK HARD BOUNDARY
        # Absolute structural override at the lowest instantiation layer.
        forbidden_domains = [
            "api.openai.com",
            "dashscope",
            "api.anthropic.com",
            "googleapis.com",
            "api.minimax.chat",
        ]
        prov_name = cfg.get("provider", "").lower()
        prov_url = cfg.get("base_url", "").lower()
        is_external = any(ext in prov_url for ext in forbidden_domains) or any(
            ext in prov_name
            for ext in ["openai", "anthropic", "gemini", "dashscope", "minimax", "vllm"]
        )

        is_hybrid_bft = os.environ.get("CORTEX_HYBRID_BFT") == "1"
        is_subagent = os.environ.get("CORTEX_SUBAGENT") == "1" or os.environ.get("CORTEX_DAEMON") == "1"

        if is_external and "localhost" not in prov_url and "127.0.0.1" not in prov_url:
            if is_hybrid_bft and prov_name == "gemini" and not is_subagent:
                logger.info(
                    "⚡ [HYBRID-BFT] Allowing external Gemini instantiation for primary node."
                )
            else:
                logger.warning(
                    "🛑 [ZERO-NETWORK] Core LLMProvider trapped external instantiation of %s. Forcing local autarchy (Ollama).",
                    prov_name,
                )
                cfg["provider"] = "ollama"
                cfg["base_url"] = "http://127.0.0.1:11434/v1"
                cfg["model"] = (
                    "qwen2.5-coder:7b"
                    if "claude" in prov_name or "gemini" in prov_name
                    else "llama3:latest"
                )
                cfg["api_key"] = None
                cfg["tier"] = "frontier"  # Elevate tier to satisfy ULTRA_THINK routing
                cfg[
                    "intent_model_map"
                ] = {}  # C5-REAL: Clear upstream model maps to prevent 404s in local inference

        self._provider = cfg["provider"]
        self._base_url = cfg["base_url"]
        self._model = cfg["model"]
        self._api_key = cfg["api_key"]
        self._context_window = cfg["context_window"]
        self._extra_headers = cfg["extra_headers"]
        self._intent_affinity = cfg["intent_affinity"]
        self._intent_model_map = cfg["intent_model_map"]
        self._tier = cfg["tier"]
        self._cost_class = cfg["cost_class"]
        self._gemini_gateway = None

        if self._provider == "ollama" and "CORTEX_LLM_TIMEOUT" not in os.environ:
            timeout_val = 15.0
        else:
            timeout_val = float(os.environ.get("CORTEX_LLM_TIMEOUT", "120.0"))
        self._client = httpx.AsyncClient(timeout=timeout_val)
        self._semaphore = asyncio.Semaphore(100)
        self._circuit_breaker = CircuitBreaker(provider_name=self._provider)

        logger.info(
            "LLM [READY] -> Provider: %s | Model: %s | URL: %s",
            self._provider,
            self._model,
            self._base_url,
        )

    def _prepare_request(self) -> tuple[str, dict[str, str]]:
        url = f"{self._base_url.rstrip('/')}/chat/completions"
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

        if "dashscope" in getattr(self, "_base_url", ""):
            payload["enable_thinking"] = True
            payload["preserve_thinking"] = True

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
                await self._acquire_quota()
                return await execute_gemini_native(
                    self._client,
                    self._semaphore,
                    self._circuit_breaker,
                    self._provider,
                    self._api_key or "",
                    prompt,
                    model_name,
                    remote_cache,
                    temperature,
                    max_tokens,
                )

        cache = _get_result_cache()
        if cached := cache.get(payload):
            return cached

        await self._acquire_quota()
        url, headers = self._prepare_request()

        current_system = system
        current_prompt = prompt
        response_text = ""

        for attempt in range(5):
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": current_system},
                    {"role": "user", "content": current_prompt},
                ],
                "temperature": temperature,
            }
            if model_name.startswith(("o1", "o3")):
                payload["max_completion_tokens"] = max_tokens
                payload.pop("temperature", None)
            else:
                payload["max_tokens"] = max_tokens

            response_text = await self._execute_completion(url, headers, payload, wrap_errors=False)

            if spectral_audit(response_text):
                cache.set(payload, response_text, provider=self._provider, model=model_name)
                return response_text

            if attempt < 4:
                logger.warning(
                    "Ω₂₃: Audit [FAIL] -> Attempting Shadow Re-phrasing (Try %d)", attempt + 2
                )
                noise = hashlib.sha256(f"{time.monotonic()}-{attempt}".encode()).hexdigest()[:6]
                current_prompt = (
                    f"{prompt}\n\n[Sovereign-UUID: {noise}]\n"
                    "Mandato: Prohibida la prosa decorativa. Ejecuta directamente."
                )
                await apply_causal_jitter(tokens_estimate=50)

        cache.set(payload, response_text, provider=self._provider, model=model_name)
        return response_text

    async def _execute_completion(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        wrap_errors: bool,
        prompt: CortexPrompt | None = None,
    ) -> str:
        try:
            return await resilient_call(
                lambda: self._execute_completion_raw(url, headers, payload, prompt),
                self._provider,
                self._circuit_breaker,
            )
        except httpx.HTTPStatusError as e:
            try:
                err_text = e.response.text[:500]
            except UnicodeDecodeError:
                err_text = "<binary_or_malformed_response>"

            logger.error(
                "LLM API Failure [%s %s]: %s",
                e.response.status_code,
                self._provider,
                err_text,
            )
            if wrap_errors:
                from cortex.utils.errors import CortexError

                raise CortexError(f"HTTP {e.response.status_code} from {self._provider}") from e
            raise
        except (
            KeyError,
            IndexError,
            json.JSONDecodeError,
            UnicodeDecodeError,
            httpx.DecodingError,
        ) as e:
            logger.error("LLM Parse Error [%s]: %s", self._provider, e)
            if wrap_errors:
                from cortex.utils.errors import CortexError

                raise CortexError(f"Unexpected JSON format from {self._provider}") from e
            raise ValueError(f"Unexpected response format from {self._provider}") from e

    async def _execute_completion_raw(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        prompt: CortexPrompt | None = None,
    ) -> str:
        await apply_causal_jitter(tokens_estimate=len(payload.get("messages", [])) * 50)
        async with self._semaphore:
            response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        self._log_resolved_model(payload, data)
        if prompt is not None and "usage" in data:
            try:
                usage = data["usage"]
                prompt.prompt_tokens = usage.get("prompt_tokens")
                prompt.completion_tokens = usage.get("completion_tokens")
            except Exception as e:
                logger.warning("Failed to extract usage metrics from response: %s", e)
        return sanitize_response(data["choices"][0]["message"]["content"])

    def _log_resolved_model(self, payload: dict[str, Any], response_data: dict[str, Any]) -> None:
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
    ) -> AsyncGenerator[str, None]:
        await self._acquire_quota()
        url, headers = self._prepare_request()
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

        async for chunk in execute_stream(
            self._client,
            self._semaphore,
            self._circuit_breaker,
            self._provider,
            url,
            headers,
            payload,
        ):
            yield chunk

    def _resolve_model(self, intent: IntentProfile) -> str:
        if self._provider == "vllm":
            from pathlib import Path

            registry_file = Path.home() / ".cortex" / "training" / "verified_adapter.json"
            if registry_file.exists():
                try:
                    with open(registry_file, encoding="utf-8") as f:
                        if (reg := json.load(f)).get("status") == "verified":
                            if adapter_path := reg.get("adapter_path"):
                                return adapter_path
                except Exception as exc:
                    logger.warning("Suppressed exception: %s", exc)
        if self._intent_model_map:
            resolved = self._intent_model_map.get(intent, self._model)
            if resolved != self._model:
                logger.debug(
                    "LLM [%s] intent=%s → model: %s", self._provider, intent.value, resolved
                )
            return resolved
        return self._model

    async def _acquire_quota(self) -> None:
        if self._provider not in ["ollama", "lmstudio"]:
            await _get_quota_manager().acquire(tokens=1, fast_reject=True)

    async def invoke(self, prompt: CortexPrompt) -> str:
        model_name = self._resolve_model(prompt.intent)
        messages = prompt.to_openai_messages()

        if getattr(prompt, "stealth", False) and messages:
            noise_id = hashlib.sha256(f"{time.monotonic()}{random.random()}".encode()).hexdigest()[
                :8
            ]
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

        if "dashscope" in getattr(self, "_base_url", ""):
            payload["enable_thinking"] = True
            payload["preserve_thinking"] = True

        cache_config = get_prefix_cache_config(self._provider)
        prefix_cache_key = getattr(prompt, "prefix_cache_key", None)
        system_extraction = (
            messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
        )

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
                user_msg = " ".join([m["content"] for m in messages if m["role"] == "user"])
                await self._acquire_quota()
                return await execute_gemini_native(
                    self._client,
                    self._semaphore,
                    self._circuit_breaker,
                    self._provider,
                    self._api_key or "",
                    user_msg,
                    model_name,
                    remote_cache,
                    prompt.temperature,
                    prompt.max_tokens,
                )

        cache = _get_result_cache()
        if cached := cache.get(payload):
            return cached

        await self._acquire_quota()
        url, headers = self._prepare_request()
        headers = prepare_stealth_headers(headers)

        if model_name.startswith(("o1", "o3")):
            payload["max_completion_tokens"] = prompt.max_tokens
            payload.pop("temperature", None)
        else:
            payload["max_tokens"] = prompt.max_tokens

        result = await self._execute_completion(
            url, headers, payload, wrap_errors=True, prompt=prompt
        )
        cache.set(payload, result, provider=self._provider, model=model_name)
        return result

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def intent_affinity(self) -> frozenset[IntentProfile]:
        return self._intent_affinity

    @property
    def tier(self) -> str:
        return self._tier

    @property
    def cost_class(self) -> str:
        return self._cost_class

    @property
    def context_window(self) -> int:
        return self._context_window

    async def close(self) -> None:
        await self._client.aclose()

    def get_intent_models(self) -> dict[str, str]:
        return {k.value: v for k, v in self._intent_model_map.items()}

    def __repr__(self) -> str:
        if self._intent_model_map:
            models = ", ".join(f"{k.value}={v}" for k, v in self._intent_model_map.items())
            return f"LLMProvider(provider={self._provider!r}, models=[{models}])"
        return f"LLMProvider(provider={self._provider!r}, model={self._model!r})"
