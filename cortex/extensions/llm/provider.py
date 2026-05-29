"""Universal LLM Provider - OpenAI-compatible async client with intent routing."""
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
from cortex.extensions.llm._resilience import CircuitBreaker, resilient_call
from cortex.extensions.llm._models import BaseProvider, CortexPrompt, IntentProfile
from cortex.extensions.llm._presets import check_api_key, get_prefix_cache_config, load_presets
from cortex.extensions.llm._result_cache import ResultCache
from cortex.extensions.llm._stealth import apply_causal_jitter, prepare_stealth_headers, sanitize_response
from cortex.extensions.llm.gemini_cache import get_gemini_gateway
from cortex.extensions.llm.quota import SovereignQuotaManager
__all__ = ['LLMProvider']
logger = logging.getLogger('cortex.extensions.llm')
_CONTENT_TYPE_JSON: Final[str] = 'application/json'
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

    def __init__(self, provider: str='qwen', api_key: str | None=None, model: str | None=None, base_url: str | None=None):
        presets = load_presets()
        if provider == 'custom':
            self._init_custom(api_key, model, base_url)
        elif provider in presets:
            self._init_preset(provider, presets[provider], api_key, model, base_url)
        else:
            supported = sorted(list(presets.keys()) + ['custom'])
            raise ValueError(f"Unknown LLM provider '{provider}'. Supported: {supported}")
        timeout_val = float(os.environ.get('CORTEX_LLM_TIMEOUT', '120.0'))
        self._client = httpx.AsyncClient(timeout=timeout_val)
        self._semaphore = asyncio.Semaphore(100)
        self._circuit_breaker = CircuitBreaker(provider_name=self._provider)
        logger.info('LLM [READY] -> Provider: %s | Model: %s | URL: %s', self._provider, self._model, self._base_url)

    async def complete(self, prompt: str, system: str='You are a helpful assistant.', temperature: float=0.0, max_tokens: int=2048, intent: IntentProfile=IntentProfile.GENERAL, prefix_cache_key: str | None=None) -> str:
        """Send a chat completion request. Returns the response text."""
        model_name = self._resolve_model(intent)
        payload: dict[str, Any] = {'model': model_name, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}], 'temperature': temperature, 'max_tokens': max_tokens}
        if 'dashscope' in getattr(self, '_base_url', ''):
            payload['enable_thinking'] = True
            payload['preserve_thinking'] = True
        cache_config = get_prefix_cache_config(self._provider)
        if cache_config.get('enabled') and prefix_cache_key and (self._provider == 'gemini'):
            if not self._gemini_gateway:
                self._gemini_gateway = get_gemini_gateway(self._api_key or '')
            remote_cache = await self._gemini_gateway.get_or_create_cache(cache_key=prefix_cache_key, system_prompt=system, model=model_name.replace('models/', ''), ttl_seconds=cache_config.get('ttl_seconds', 3600))
            if remote_cache:
                return await self._execute_gemini_native(prompt=prompt, model_name=model_name, remote_cache=remote_cache, temperature=temperature, max_tokens=max_tokens)
        cache = _get_result_cache()
        if (cached := cache.get(payload)):
            return cached
        await _get_quota_manager().acquire(tokens=1)
        url, headers = self._prepare_request()
        current_system = system
        response_text = ''
        for attempt in range(5):
            payload = {'model': model_name, 'messages': [{'role': 'system', 'content': current_system}, {'role': 'user', 'content': prompt}], 'temperature': temperature}
            if model_name.startswith(('o1', 'o3')):
                payload['max_completion_tokens'] = max_tokens
                payload.pop('temperature', None)
            else:
                payload['max_tokens'] = max_tokens
            response_text = await self._execute_completion(url, headers, payload, wrap_errors=False)
            if spectral_audit(response_text):
                cache.set(payload, response_text, provider=self._provider, model=model_name)
                return response_text
            if attempt < 4:
                logger.warning('Ω₂₃: Audit [FAIL] -> Attempting Shadow Re-phrasing (Try %d)', attempt + 2)
                noise = hashlib.sha256(f'{time.monotonic()}-{attempt}'.encode()).hexdigest()[:6]
                current_system = f'{system}\n\n[Sovereign-UUID: {noise}]\nMandato: Prohibida la prosa decorativa. Ejecuta directamente.'
                await apply_causal_jitter(tokens_estimate=50)
        cache.set(payload, response_text, provider=self._provider, model=model_name)
        return response_text

    async def stream(self, prompt: str, system: str='You are a helpful assistant.', temperature: float=0.0, max_tokens: int=2048, intent: IntentProfile=IntentProfile.GENERAL) -> None:
        """Stream a chat completion request. Yields text chunks."""
        await _get_quota_manager().acquire(tokens=1)
        url, headers = self._prepare_request()
        headers = prepare_stealth_headers(headers)
        model_name = self._resolve_model(intent)
        payload = {'model': model_name, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}], 'temperature': temperature, 'stream': True}
        if model_name.startswith(('o1', 'o3')):
            payload['max_completion_tokens'] = max_tokens
            payload.pop('temperature', None)
        else:
            payload['max_tokens'] = max_tokens
        try:
            last_exc = None
            max_attempts = 3
            yielded_any = False
            for attempt in range(1, max_attempts + 1):
                start_time = time.monotonic()
                try:
                    async with self._circuit_breaker:
                        async with self._semaphore:
                            async with self._client.stream('POST', url, headers=headers, json=payload) as response:
                                response.raise_for_status()
                                latency = time.monotonic() - start_time
                                logger.info('LLM Stream [CONNECTED] -> Provider: %s | Latency: %.2fs | Attempt: %d', self._provider, latency, attempt)
                                async for chunk in self._process_stream_lines(response):
                                    yield chunk
                                    yielded_any = True
                                return
                except Exception as e:
                    from cortex.extensions.llm._resilience import CircuitBreakerError, is_retryable
                    latency = time.monotonic() - start_time
                    last_exc = e
                    if yielded_any:
                        logger.error('LLM Stream [FAIL-MIDSTREAM] -> Provider: %s | Error: %s. Cannot retry after partial yield.', self._provider, type(e).__name__)
                        raise
                    if isinstance(e, CircuitBreakerError):
                        raise
                    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (400, 401, 403):
                        raise
                    if not is_retryable(e) or attempt == max_attempts:
                        raise
                    delay = min(1.0 * 2 ** (attempt - 1), 30.0)
                    sleep_s = delay + delay * 0.1 * random.uniform(-1, 1)
                    logger.warning('LLM Stream [RETRY] -> Provider: %s | Error: %s | Next try in %.2fs', self._provider, type(e).__name__, sleep_s)
                    await asyncio.sleep(sleep_s)
            if last_exc:
                raise last_exc
        except httpx.HTTPStatusError as e:
            logger.error('LLM Stream Failure [%s]: %s', self._provider, e.response.text[:500])
            raise

    async def invoke(self, prompt: CortexPrompt) -> str:
        """Traduce el CortexPrompt al formato nativo del LLM y ejecuta la inferencia."""
        model_name = self._resolve_model(prompt.intent)
        messages = prompt.to_openai_messages()
        if getattr(prompt, 'stealth', False) and messages:
            noise_id = hashlib.sha256(f'{time.monotonic()}{random.random()}'.encode()).hexdigest()[:8]
            for msg in reversed(messages):
                if msg['role'] == 'user':
                    msg['content'] += f'\n\n<!-- ctx:{noise_id} -->'
                    msg['content'] = ' ' * random.randint(0, 2) + msg['content']
                    break
            await apply_causal_jitter(tokens_estimate=50)
        payload: dict[str, Any] = {'model': model_name, 'messages': messages, 'temperature': prompt.temperature}
        if 'dashscope' in getattr(self, '_base_url', ''):
            payload['enable_thinking'] = True
            payload['preserve_thinking'] = True
        cache_config = get_prefix_cache_config(self._provider)
        prefix_cache_key = getattr(prompt, 'prefix_cache_key', None)
        system_extraction = ''
        if messages and messages[0]['role'] == 'system':
            system_extraction = messages[0]['content']
        if cache_config.get('enabled') and prefix_cache_key and (self._provider == 'gemini'):
            if not self._gemini_gateway:
                self._gemini_gateway = get_gemini_gateway(self._api_key or '')
            remote_cache = await self._gemini_gateway.get_or_create_cache(cache_key=prefix_cache_key, system_prompt=system_extraction, model=model_name.replace('models/', ''), ttl_seconds=cache_config.get('ttl_seconds', 3600))
            if remote_cache:
                user_msg = ' '.join([m['content'] for m in messages if m['role'] == 'user'])
                return await self._execute_gemini_native(prompt=user_msg, model_name=model_name, remote_cache=remote_cache, temperature=prompt.temperature, max_tokens=prompt.max_tokens)
        cache = _get_result_cache()
        if (cached := cache.get(payload)):
            return cached
        await _get_quota_manager().acquire(tokens=1)
        url, headers = self._prepare_request()
        headers = prepare_stealth_headers(headers)
        if model_name.startswith(('o1', 'o3')):
            payload['max_completion_tokens'] = prompt.max_tokens
            payload.pop('temperature', None)
        else:
            payload['max_tokens'] = prompt.max_tokens
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
            models = ', '.join((f'{k.value}={v}' for k, v in self._intent_model_map.items()))
            return f'LLMProvider(provider={self._provider!r}, models=[{models}])'
        return f'LLMProvider(provider={self._provider!r}, model={self._model!r})'
