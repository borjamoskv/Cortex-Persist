# This file is part of CORTEX. Apache-2.0. Change Date: 2030-01-01.

<<<<<<< HEAD
"""Universal LLM Provider - OpenAI-compatible async client with intent routing."""
=======
"""Universal LLM Provider — OpenAI-compatible async client with intent routing."""
>>>>>>> origin/main

from __future__ import annotations

import asyncio
<<<<<<< HEAD
import hashlib
import json
import logging
import os
import random
import time
from typing import Any

import httpx

from cortex.extensions.llm._audit import spectral_audit
from cortex.extensions.llm._backoff import handle_429_backoff
from cortex.extensions.llm._models import BaseProvider, CortexPrompt, IntentProfile
from cortex.extensions.llm._presets import load_presets

# Modular Internal Imports
from cortex.extensions.llm._stealth import (
    apply_causal_jitter,
    prepare_stealth_headers,
    sanitize_response,
)
from cortex.extensions.llm.quota import SovereignQuotaManager
=======
import json
import logging
import os
import re
from typing import Any, Final, Optional

import httpx

from cortex.extensions.llm._presets import load_presets
from cortex.extensions.llm.quota import SovereignQuotaManager
from cortex.extensions.llm.router import BaseProvider, CortexPrompt, IntentProfile
>>>>>>> origin/main

__all__ = ["LLMProvider"]

logger = logging.getLogger("cortex.extensions.llm")
<<<<<<< HEAD
_QUOTA_MANAGER = SovereignQuotaManager()


=======

_CONTENT_TYPE_JSON: Final[str] = "application/json"
_QUOTA_MANAGER = SovereignQuotaManager()


# ─── Implementation ───────────────────────────────────────────────────


>>>>>>> origin/main
class LLMProvider(BaseProvider):
    """Universal OpenAI-compatible async LLM client.

    Works with ANY endpoint that speaks the OpenAI chat completions
    protocol. Use a preset name or 'custom' with explicit URL/key/model.
<<<<<<< HEAD
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
=======

    Usage::

        provider = LLMProvider(provider="qwen")
        answer = await provider.complete("What is CORTEX?")
    """

    # Note: Enforces temperature=0.0 in prompts to guarantee deterministic swarm behavior
    def __init__(
        self,
        provider: str = "qwen",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        presets = load_presets()

>>>>>>> origin/main
        if provider == "custom":
            self._init_custom(api_key, model, base_url)
        elif provider in presets:
            self._init_preset(provider, presets[provider], api_key, model, base_url)
<<<<<<< HEAD
=======

>>>>>>> origin/main
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

<<<<<<< HEAD
    def _init_custom(self, api_key: str | None, model: str | None, base_url: str | None) -> None:
=======
    def _init_custom(
        self,
        api_key: Optional[str],
        model: Optional[str],
        base_url: Optional[str],
    ) -> None:
        """Initialize a custom provider configuration."""
>>>>>>> origin/main
        self._provider = "custom"
        self._base_url = base_url or os.environ.get("CORTEX_LLM_BASE_URL")
        self._model = model or os.environ.get("CORTEX_LLM_MODEL", "gpt-4")
        self._api_key = api_key or os.environ.get("CORTEX_LLM_API_KEY")
        self._context_window = 128000
        self._extra_headers = {}
        self._intent_affinity: frozenset[IntentProfile] = frozenset({IntentProfile.GENERAL})
<<<<<<< HEAD
        self._intent_model_map: dict[IntentProfile, str] = {}
=======
        self._intent_model_map: dict[IntentProfile, str] = {}  # no map for custom
>>>>>>> origin/main
        self._tier = "high"
        self._cost_class = "medium"

        if not self._base_url:
            raise ValueError("Custom LLM provider requires CORTEX_LLM_BASE_URL")

    def _init_preset(
        self,
        provider: str,
        preset: dict[str, Any],
<<<<<<< HEAD
        api_key: str | None,
        model: str | None,
        base_url: str | None,
    ) -> None:
        self._provider = provider
        self._base_url = base_url or preset["base_url"]
        self._model = model or os.environ.get("CORTEX_LLM_MODEL") or preset["default_model"]
=======
        api_key: Optional[str],
        model: Optional[str],
        base_url: Optional[str],
    ) -> None:
        """Initialize from a known provider preset."""
        self._provider = provider
        self._base_url = base_url or preset["base_url"]
        self._model = model or os.environ.get("CORTEX_LLM_MODEL") or preset["default_model"]
        self._context_window = preset["context_window"]
>>>>>>> origin/main
        self._extra_headers = preset.get("extra_headers", {})
        self._api_key = api_key
        self._tier = preset.get("tier", "high")
        self._cost_class = preset.get("cost_class", "medium")

<<<<<<< HEAD
=======
        # Resolve intent affinity from preset specialization tags
>>>>>>> origin/main
        _TAG_MAP: dict[str, IntentProfile] = {
            "code": IntentProfile.CODE,
            "reasoning": IntentProfile.REASONING,
            "creative": IntentProfile.CREATIVE,
            "architect": IntentProfile.ARCHITECT,
            "general": IntentProfile.GENERAL,
        }
        raw_specs: list[str] = preset.get("specialization", ["general"])
<<<<<<< HEAD
        self._intent_affinity = frozenset(
            _TAG_MAP[t] for t in raw_specs if t in _TAG_MAP
        ) or frozenset({IntentProfile.GENERAL})

        raw_map: dict[str, str] = preset.get("intent_model_map", {})
        self._intent_model_map = {
            _TAG_MAP[tag]: mid for tag, mid in raw_map.items() if tag in _TAG_MAP
        }

=======
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
>>>>>>> origin/main
        env_key = preset.get("env_key") or preset.get("api_key_env")
        if not self._api_key and env_key:
            self._api_key = os.environ.get(env_key)

<<<<<<< HEAD
        if not self._api_key and provider not in ["ollama", "lmstudio", "llamacpp", "vllm", "jan"]:
            raise ValueError(f"Provider '{provider}' requires API key ({env_key})")

    def _prepare_request(self) -> tuple[str, dict[str, str]]:
        url = f"{self._base_url.rstrip('/')}/chat/completions"
        headers = prepare_stealth_headers(self._extra_headers)
=======
        if not self._api_key:
            # Some providers like Ollama don't need keys
            if provider not in ["ollama", "lmstudio", "llamacpp", "vllm", "jan"]:
                msg = f"LLM provider '{provider}' requires an API key "
                msg += f"(api_key argument or {env_key} env var)"
                raise ValueError(msg)

    def _prepare_request(self) -> tuple[str, dict[str, str]]:
        # type: ignore[reportOptionalMemberAccess]
        url = f"{self._base_url.rstrip('/')}/chat/completions"  # type: ignore[reportOptionalMemberAccess]
        headers: dict[str, str] = {
            "Content-Type": _CONTENT_TYPE_JSON,
            **self._extra_headers,
        }
>>>>>>> origin/main
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
    ) -> str:
<<<<<<< HEAD
        await _QUOTA_MANAGER.acquire(tokens=1)
        url, headers = self._prepare_request()
        model_name = self._resolve_model(intent)

        current_system = system
        for attempt in range(3):
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": current_system},
                    {"role": "user", "content": prompt}
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
                return response_text

            if attempt < 2:
                logger.warning(
                    "Ω₂₃: Audit [FAIL] -> Attempting Shadow Re-phrasing (Try %d)", attempt + 2
                )
                # Use SHA256 for security compliance (AX-021)
                noise = hashlib.sha256(f"{time.time()}-{attempt}".encode()).hexdigest()[:6]
                current_system = f"{system}\n\n[Sovereign-UUID: {noise}]\n" \
                                 "Mandato: Prohibida la prosa decorativa. Ejecuta directamente."
                await self._apply_causal_jitter(tokens_estimate=50)

        return response_text

    async def _apply_causal_jitter(self, tokens_estimate: int = 100):
        await apply_causal_jitter(tokens_estimate)
=======
        """Send a chat completion request. Returns the response text.

        Args:
            intent: Intent profile for model selection. When the provider has an
                ``intent_model_map``, this selects the optimal model for the task.
        """
        await _QUOTA_MANAGER.acquire(tokens=1)
        url, headers = self._prepare_request()

        model_name = self._resolve_model(intent)
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        if model_name.startswith("o1") or model_name.startswith("o3"):
            payload["max_completion_tokens"] = max_tokens
            payload.pop("temperature", None)
        else:
            payload["max_tokens"] = max_tokens

        return await self._execute_completion(url, headers, payload, wrap_errors=False)
>>>>>>> origin/main

    async def _execute_completion(
        self, url: str, headers: dict[str, str], payload: dict[str, Any], wrap_errors: bool
    ) -> str:
        try:
            return await self._execute_completion_raw(url, headers, payload)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
<<<<<<< HEAD
                return await handle_429_backoff(self, url, headers, payload, e)
            logger.error(
                "LLM API Failure [%s %s]: %s",
                e.response.status_code, self._provider, e.response.text[:500]
            )
            if wrap_errors:
                from cortex.utils.errors import CortexError
                raise CortexError(
                    f"HTTP {e.response.status_code} from {self._provider}"
                ) from e
=======
                return await self._handle_429_backoff(url, headers, payload, e)

            logger.error(
                "LLM API Failure [%s %s]: %s",
                e.response.status_code,
                self._provider,
                e.response.text[:500],
            )
            if wrap_errors:
                from cortex.utils.errors import CortexError

                raise CortexError(f"HTTP {e.response.status_code} from {self._provider}") from e
>>>>>>> origin/main
            raise
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error("LLM Parse Error [%s]: %s", self._provider, e)
            if wrap_errors:
                from cortex.utils.errors import CortexError
<<<<<<< HEAD
                msg = f"Unexpected JSON format from {self._provider}"
                raise CortexError(msg) from e
            err = f"Unexpected response format from {self._provider}"
            raise ValueError(err) from e
=======

                raise CortexError(f"Unexpected JSON format from {self._provider}") from e
            raise ValueError(f"Unexpected response format from {self._provider}") from e
>>>>>>> origin/main

    async def _execute_completion_raw(
        self, url: str, headers: dict[str, str], payload: dict[str, Any]
    ) -> str:
<<<<<<< HEAD
        await self._apply_causal_jitter(tokens_estimate=len(payload.get("messages", [])) * 50)
=======
        """Executes a single completion attempt directly. Throws native exceptions."""
>>>>>>> origin/main
        async with self._semaphore:
            response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        self._log_resolved_model(payload, data)
<<<<<<< HEAD
        raw_content = data["choices"][0]["message"]["content"]
        return sanitize_response(raw_content)

    def _log_resolved_model(self, payload: dict[str, Any], response_data: dict[str, Any]) -> None:
=======
        return data["choices"][0]["message"]["content"]

    def _log_resolved_model(self, payload: dict[str, Any], response_data: dict[str, Any]) -> None:
        """Log when a meta-router resolves to a different model than requested.

        Enables traceability for hierarchical routing — when CORTEX
        requests 'openrouter/auto' and OpenRouter resolves to e.g.
        'anthropic/claude-3.5-sonnet', this captures both layers.
        """
>>>>>>> origin/main
        requested = payload.get("model", "")
        actual = response_data.get("model", requested)
        if actual and actual != requested:
            logger.info(
                "LLM [%s] meta-routed: requested=%s → resolved=%s",
                self._provider,
                requested,
                actual,
            )

<<<<<<< HEAD
=======
    def _extract_retry_delay(self, text: str) -> Optional[float]:
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
        original_error: httpx.HTTPStatusError,
    ) -> str:
        """Maneja el backoff rápido o el fallback hipersónico para errores 429.

        Aplica Path B (Ejecución Hipersónica):
        1. Para OpenAI: Breve backoff (max 3 intentos) dada su resiliencia.
        2. Otros (ej. Gemini): Fallback INSTANTÁNEO sin dormir (O(1)).
        """
        if self._provider != "openai":
            logger.warning(
                "LLM API [429 Quota Exceeded Final] on %s. Fallback inmediato al meta-router...",
                self._model,
            )
            # En vez de ahogar la máquina, propaga instantáneamente hacia el Router (Orchestra)
            # para que haga el fallback hipersónico al siguiente modelo disponible en la cascada.
            raise original_error

        # Solo si es OpenAI le damos un respiro muy breve
        last_error = original_error
        for attempt in range(1, 4):
            # Reducimos los tiempos drásticamente para agilizar el YOLO
            safe_delay = (attempt * 1.5) + (1.0 * attempt)

            logger.warning(
                "LLM API [429 Quota Exceeded] on %s. Auto-sleeping for %.2fs (attempt %d/3)...",
                self._model,
                safe_delay,
                attempt,
            )
            await asyncio.sleep(safe_delay)

            try:
                return await self._execute_completion_raw(url, headers, payload)
            except httpx.HTTPStatusError as e2:
                if e2.response.status_code == 429:
                    last_error = e2
                    continue
                raise original_error from e2
            except (httpx.HTTPError, ValueError, KeyError) as retry_e:
                logger.error("LLM Quota Retry Failure: %s", retry_e)
                raise original_error from retry_e

        return await self._execute_fallback(payload, last_error)

    async def _execute_fallback(
        self, payload: dict[str, Any], original_error: httpx.HTTPStatusError
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
        except (httpx.HTTPError, ValueError, KeyError) as fallback_e:
            logger.error("LLM Fallback Failure: %s", fallback_e)
            raise original_error from fallback_e
        finally:
            await fallback_provider.close()

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

>>>>>>> origin/main
    async def stream(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        intent: IntentProfile = IntentProfile.GENERAL,
    ):
<<<<<<< HEAD
        await _QUOTA_MANAGER.acquire(tokens=1)
        url, headers = self._prepare_request()
        from cortex.config import LLM_STEALTH_MODE

        if LLM_STEALTH_MODE:
            headers = prepare_stealth_headers(headers)
=======
        """Stream a chat completion request. Yields text chunks.

        Args:
            intent: Intent profile for model selection. When the provider has an
                ``intent_model_map``, this selects the optimal model for the task.
        """
        await _QUOTA_MANAGER.acquire(tokens=1)
        url, headers = self._prepare_request()

>>>>>>> origin/main
        model_name = self._resolve_model(intent)
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system},
<<<<<<< HEAD
                {"role": "user", "content": prompt}
=======
                {"role": "user", "content": prompt},
>>>>>>> origin/main
            ],
            "temperature": temperature,
            "stream": True,
        }
<<<<<<< HEAD
        if model_name.startswith(("o1", "o3")):
=======
        if model_name.startswith("o1") or model_name.startswith("o3"):
>>>>>>> origin/main
            payload["max_completion_tokens"] = max_tokens
            payload.pop("temperature", None)
        else:
            payload["max_tokens"] = max_tokens

        try:
            async with self._semaphore:
                async with self._client.stream(
<<<<<<< HEAD
                    "POST", url, headers=headers, json=payload
=======
                    "POST",
                    url,
                    headers=headers,
                    json=payload,
>>>>>>> origin/main
                ) as response:
                    response.raise_for_status()
                    async for chunk in self._process_stream_lines(response):
                        yield chunk
<<<<<<< HEAD
        except httpx.HTTPStatusError:
            logger.error("LLM Stream Failure [%s]", self._provider)
            raise

    async def _process_stream_lines(self, response: httpx.Response):
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
        if self._intent_model_map:
            return self._intent_model_map.get(intent, self._model)
        return self._model

    async def invoke(self, prompt: CortexPrompt) -> str:
        await _QUOTA_MANAGER.acquire(tokens=1)
        url, headers = self._prepare_request()
        from cortex.config import LLM_STEALTH_MODE

        if LLM_STEALTH_MODE:
            headers = prepare_stealth_headers(headers)
        model_name = self._resolve_model(prompt.intent)
        messages = prompt.to_openai_messages()

        if LLM_STEALTH_MODE and messages and messages[0]["role"] == "system":
            # Use SHA256 for security compliance (AX-021)
            noise_id = hashlib.sha256(f"{time.time()}{random.random()}".encode()).hexdigest()[:8]
            messages[0]["content"] += f"\n\n<!-- ctx:{noise_id} -->"
            messages[0]["content"] = (" " * random.randint(0, 2)) + messages[0]["content"]

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": prompt.temperature
        }
        if model_name.startswith(("o1", "o3")):
=======
        except httpx.HTTPStatusError as e:
            logger.error(
                "LLM Stream Failure [%s]: %s",
                self._provider,
                e.response.text[:500],
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
        await _QUOTA_MANAGER.acquire(tokens=1)
        url, headers = self._prepare_request()

        model_name = self._resolve_model(prompt.intent)
        payload = {
            "model": model_name,
            "messages": prompt.to_openai_messages(),
            "temperature": prompt.temperature,
        }
        if model_name.startswith("o1") or model_name.startswith("o3"):
>>>>>>> origin/main
            payload["max_completion_tokens"] = prompt.max_tokens
            payload.pop("temperature", None)
        else:
            payload["max_tokens"] = prompt.max_tokens

        return await self._execute_completion(url, headers, payload, wrap_errors=True)

    @property
    def model_name(self) -> str:
<<<<<<< HEAD
        """Nombre del modelo subyacente (BaseProvider contract)."""
=======
        """Active model name (alias for ``model``)."""
        return self._model

    @property
    def model(self) -> str:
        """Active model name."""
>>>>>>> origin/main
        return self._model

    @property
    def provider_name(self) -> str:
<<<<<<< HEAD
        """Identificador único del proveedor (BaseProvider contract)."""
=======
        """Provider identifier."""
>>>>>>> origin/main
        return self._provider

    @property
    def intent_affinity(self) -> frozenset[IntentProfile]:
<<<<<<< HEAD
=======
        """Intenciones para las que este provider es óptimo."""
>>>>>>> origin/main
        return self._intent_affinity

    @property
    def tier(self) -> str:
<<<<<<< HEAD
=======
        """Provider tier from preset (frontier/high/local)."""
>>>>>>> origin/main
        return self._tier

    @property
    def cost_class(self) -> str:
<<<<<<< HEAD
=======
        """Cost class from preset (free/low/medium/high/variable)."""
>>>>>>> origin/main
        return self._cost_class

    @property
    def context_window(self) -> int:
<<<<<<< HEAD
        from cortex.extensions.llm._presets import resolve_context_window

        return resolve_context_window(self._provider, self._model)

    async def close(self) -> None:
        await self._client.aclose()

    def get_intent_models(self) -> dict[str, str]:
        return {k.value: v for k, v in self._intent_model_map.items()}

=======
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

>>>>>>> origin/main
    def __repr__(self) -> str:
        if self._intent_model_map:
            models = ", ".join(f"{k.value}={v}" for k, v in self._intent_model_map.items())
            return f"LLMProvider(provider={self._provider!r}, models=[{models}])"
        return f"LLMProvider(provider={self._provider!r}, model={self._model!r})"
