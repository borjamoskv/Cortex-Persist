# [C5-REAL] Exergy-Maximized
"""LLM Router.

Enrutador resiliente con routing determinista por intención.
Implementa Strategy + Circuit Breaker + ROP (Ω₂ Landauer split).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from cortex.extensions.llm._cascade import CascadeManager, classify_tier
from cortex.extensions.llm._models import (
    BaseProvider,
    CascadeEvent,
    CascadeTier,
    CortexPrompt,
    HedgedResult,
    IntentProfile,
    ReasoningMode,
)
from cortex.extensions.llm._router_hedging import execute_hedged, execute_swarm
from cortex.extensions.llm._router_policy import ordered_fallbacks
from cortex.extensions.llm._router_shannon import compress_working_memory
from cortex.extensions.llm._telemetry import CascadeTelemetry
from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex_extensions.llm.router")

__all__ = [
    "BaseProvider",
    "CascadeEvent",
    "CascadeTier",
    "CortexLLMRouter",
    "CortexPrompt",
    "HedgedResult",
    "IntentProfile",
]


class CortexLLMRouter:
    """Enrutador resiliente con routing determinista por intención."""

    # Default safety margin: keep prompts under 90% of model window.
    _CONTEXT_SAFETY_MARGIN: float = 0.90
    _COMPRESSED_TAIL_MESSAGES: int = 6

    def __init__(
        self,
        primary: BaseProvider,
        fallbacks: Sequence[BaseProvider] | None = None,
        *,
        negative_ttl: float = 300.0,
        positive_ttl: float = 600.0,
        hedging_providers: Sequence[BaseProvider] | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        self._primary = primary
        self._fallbacks = list(fallbacks or [])
        self._hedging_providers = list(hedging_providers or [])
        self._cascade = CascadeManager(negative_ttl, positive_ttl)
        self._telemetry = CascadeTelemetry(db_path=str(db_path) if db_path else None)
        # Thermal Heat-Sink: coalesce identical inflight prompts (Ω₂)
        self._inflight: dict[str, asyncio.Future[Result[str, str]]] = {}
        self._evicted: set[str] = set()

    @property
    def primary(self) -> BaseProvider:
        return self._primary

    @property
    def fallbacks(self) -> list[BaseProvider]:
        return self._fallbacks

    def _ordered_fallbacks(self, prompt: CortexPrompt | IntentProfile) -> list[BaseProvider]:
        """Ordena fallbacks: intent affinity → A-record → cost → tier."""
        return ordered_fallbacks(self._cascade, self._fallbacks, prompt)

    async def execute_hedged(self, prompt: CortexPrompt) -> Result[str, str] | None:
        """Attempt hedged (parallel) execution if peers are available."""
        return await execute_hedged(prompt, self._hedging_providers, self._cascade, self._telemetry)

    async def execute_swarm(self, prompt: CortexPrompt) -> Result[str, str] | None:
        """Ω₂₁: Parallel Swarm Racing."""
        fallbacks = self._ordered_fallbacks(prompt)
        return await execute_swarm(prompt, self._primary, fallbacks, self._cascade, self._telemetry)

    def clear_positive_cache(self) -> None:
        """Clear A-records."""
        self._cascade._a_records.clear()

    def clear_negative_cache(self) -> None:
        """Clear NXDOMAIN records."""
        self._cascade._nxdomain_cache.clear()

    async def execute_resilient(self, prompt: CortexPrompt) -> Result[str, str]:
        """Ejecuta inferencia con cascade determinista por intención."""
        # Dynamic threshold based on provider context window (Ω₁₃)
        model_window = getattr(self._primary, "context_window", 32000)
        max_words = int((model_window * self._CONTEXT_SAFETY_MARGIN) * 0.75)

        prompt.working_memory = compress_working_memory(
            prompt.working_memory,
            max_words,
            self._COMPRESSED_TAIL_MESSAGES,
        )

        # Thermal Heat-Sink: coalesce identical concurrent requests (Ω₂)
        wm_hash = hash(tuple((m.get("role"), m.get("content")) for m in prompt.working_memory))
        prompt_key = str(
            hash(
                (
                    hash(prompt.system_instruction) if prompt.system_instruction else 0,
                    wm_hash,
                    prompt.intent,
                )
            )
        )

        if prompt_key in self._inflight:
            logger.debug(
                "🔥 [HEAT-SINK] Coalescing duplicate inflight prompt: %s...", prompt_key[:8]
            )
            return await self._inflight[prompt_key]

        loop = asyncio.get_running_loop()
        future: asyncio.Future[Result[str, str]] = loop.create_future()
        self._inflight[prompt_key] = future

        try:
            result = await self._execute_resilient_impl(prompt)
            future.set_result(result)
            return result
        except Exception as exc:
            if not future.done():
                future.set_exception(exc)
            raise
        finally:
            self._inflight.pop(prompt_key, None)

    async def invoke(self, prompt: CortexPrompt) -> Result[str, str]:
        """Alias for backward compatibility."""
        return await self.execute_resilient(prompt)

    async def route(
        self, prompt: CortexPrompt, provider_hint: str | None = None
    ) -> Result[str, str]:
        """Dispatch a prompt with optional provider override (hint) and Dynamic Cache Routing."""
        if not provider_hint and prompt.system_instruction:
            # Implement Cache-Aware Routing (Zero-Recompute Policy)
            try:
                from cortex.extensions.swarm.kv_prefix_registry import get_kv_registry

                registry = get_kv_registry()
                hot_providers = registry.check_cache_affinity(prompt.system_instruction)
                if hot_providers:
                    valid_providers = {self._primary.provider_name} | {
                        p.provider_name for p in self._fallbacks
                    }
                    for hp in hot_providers:
                        if hp in valid_providers:
                            provider_hint = hp
                            logger.info(
                                "🔥 [CACHE-ROUTING] Affinity detected correctly in %s. Routing directly.",
                                hp,
                            )
                            break
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)

        if not provider_hint or self._primary.provider_name == provider_hint:
            return await self.execute_resilient(prompt)

        # Provider Hint: temporarily swap priority for this request
        for p in self._fallbacks:
            if p.provider_name == provider_hint:
                logger.debug("🎯 [ROUTING] Overriding primary with hint: %s", provider_hint)
                res = await self._try_provider(p, prompt)
                if res.is_ok():
                    return res
                break

        return await self.execute_resilient(prompt)

    async def _execute_resilient_impl(self, prompt: CortexPrompt) -> Result[str, str]:
        """Core cascade logic."""
        # Phase 0.1: Parallel Swarm Racing (Ω₂₁)
        if prompt.swarm_mode:
            swarm_res = await self.execute_swarm(prompt)
            if swarm_res:
                return swarm_res

        # Phase 0.2: Standard Hedging (Parallel race-to-first)
        hedged_res = await self.execute_hedged(prompt)
        if hedged_res:
            return hedged_res

        # Phase 1: Primary sequential attempt
        start = time.monotonic()
        primary_valid = True

        reasoning_mode = getattr(prompt, "reasoning_mode", None)
        if reasoning_mode == ReasoningMode.ULTRA_THINK:
            if getattr(self._primary, "tier", None) != "frontier":
                primary_valid = False

        if self._primary.provider_name in self._evicted:
            primary_valid = False

        errors = []
        if primary_valid:
            res_primary = await self._try_provider(self._primary, prompt)
            latency = (time.monotonic() - start) * 1000

            if res_primary.is_ok():
                self._telemetry.emit(
                    CascadeEvent(
                        intent=prompt.intent,
                        resolved_by=self._primary.provider_name,
                        project=prompt.project,
                        tier=CascadeTier.PRIMARY,
                        depth=1,
                        latency_ms=latency,
                        prompt_tokens=prompt.prompt_tokens,
                        completion_tokens=prompt.completion_tokens,
                    )
                )
                return res_primary
            errors.append(f"Primary ({self._primary.provider_name}): {res_primary.error}")  # type: ignore
        else:
            if self._primary.provider_name in self._evicted:
                errors.append(f"Primary ({self._primary.provider_name}): Skipped (Evicted via 401)")
            else:
                errors.append(
                    f"Primary ({self._primary.provider_name}): Skipped (ULTRA_THINK requires frontier tier)"
                )

        # Phase 2: Fallback cascade
        fallbacks = self._ordered_fallbacks(prompt)
        
        is_fast_reject = False
        if not primary_valid:
            # Primary was skipped, not a fast reject
            pass
        elif res_primary.error and ("Fast-Reject" in res_primary.error or "429" in res_primary.error):
            is_fast_reject = True

        valid_fallbacks = []
        for provider in fallbacks:
            if provider.provider_name in self._evicted:
                errors.append(f"{provider.provider_name}: Skip (Evicted via 401)")
                continue
            if self._cascade.is_nxdomain_cached(provider.provider_name):
                errors.append(f"{provider.provider_name}: Skip (NXDOMAIN cached)")
                continue
            valid_fallbacks.append(provider)

        # Si el primario tuvo un Fast-Reject, corremos los fallbacks en paralelo (Zero-Wait tuning)
        if is_fast_reject and valid_fallbacks:
            logger.warning(
                "🚀 [ZERO-WAIT FAILOVER] Primary Fast-Rejected. Racing %d fallbacks simultaneously...",
                len(valid_fallbacks),
            )
            from cortex.extensions.llm._hedging import HedgedRequestStrategy
            
            fb_start = time.monotonic()
            hedged_res, hedge_errors = await HedgedRequestStrategy.race(valid_fallbacks, prompt)
            fb_latency = (time.monotonic() - fb_start) * 1000
            
            if hedged_res:
                winner_provider = next(p for p in valid_fallbacks if p.provider_name == hedged_res.winner)
                tier = classify_tier(winner_provider, prompt.intent)
                self._cascade.set_a_record(hedged_res.winner, fb_latency)
                self._telemetry.emit(
                    CascadeEvent(
                        intent=prompt.intent,
                        resolved_by=hedged_res.winner,
                        project=prompt.project,
                        tier=tier,
                        depth=2,  # Represents a fallback
                        latency_ms=fb_latency,
                        errors=errors,
                        prompt_tokens=prompt.prompt_tokens,
                        completion_tokens=prompt.completion_tokens,
                    )
                )
                return Ok(hedged_res.response)
            
            # If the race failed, all fallbacks failed
            for err in hedge_errors:
                errors.append(err)
            for provider in valid_fallbacks:
                self._cascade.set_nx_record(provider.provider_name)
        else:
            # Fallback cascade secuencial tradicional
            for i, provider in enumerate(valid_fallbacks, start=2):
                fb_start = time.monotonic()
                res_fb = await self._try_provider(provider, prompt)
                fb_latency = (time.monotonic() - fb_start) * 1000

                if res_fb.is_ok():
                    tier = classify_tier(provider, prompt.intent)
                    self._cascade.set_a_record(provider.provider_name, fb_latency)
                    self._telemetry.emit(
                        CascadeEvent(
                            intent=prompt.intent,
                            resolved_by=provider.provider_name,
                            project=prompt.project,
                            tier=tier,
                            depth=i,
                            latency_ms=fb_latency,
                            errors=errors,
                            prompt_tokens=prompt.prompt_tokens,
                            completion_tokens=prompt.completion_tokens,
                        )
                    )
                    return res_fb

                errors.append(f"{provider.provider_name}: {res_fb.error}")  # type: ignore
                self._cascade.set_nx_record(provider.provider_name)

        self._telemetry.emit(
            CascadeEvent(
                intent=prompt.intent,
                resolved_by=None,
                project=prompt.project,
                tier=CascadeTier.NONE,
                depth=len(fallbacks) + 1,
                latency_ms=(time.monotonic() - start) * 1000,
                errors=errors,
            )
        )
        return Err(f"All providers failed. Cascade exhausted. Errors: {'; '.join(errors)}")

    async def _try_provider(self, provider: BaseProvider, prompt: CortexPrompt) -> Result[str, str]:
        """Try a single provider, returning Result."""
        import httpx

        from cortex.extensions.llm.quota import QuotaRejectedError

        # [LOCAL-INFERENCE-OMEGA] ZERO-NETWORK HARD BOUNDARY
        # All semantic ignition MUST occur on local silicon.
        forbidden_domains = ["api.openai.com", "dashscope", "api.anthropic.com", "googleapis.com", "api.minimax.chat"]
        provider_url = str(getattr(provider, "base_url", "")).lower()
        provider_name = getattr(provider, "provider_name", "").lower()
        
        is_external = any(ext in provider_url for ext in forbidden_domains) or \
                      any(ext in provider_name for ext in ["openai", "anthropic", "gemini", "dashscope", "minimax"])
                      
        if is_external and "localhost" not in provider_url and "127.0.0.1" not in provider_url:
            logger.warning(
                "🛑 [ZERO-NETWORK] Trapped external route for %s. Re-routing exclusively through localhost:11434.",
                provider.provider_name
            )
            # DYNAMIC RE-ROUTING: Instantiate local provider to ensure no external logic leaks
            from cortex.extensions.llm.provider import LLMProvider
            local_model = "qwen2.5-coder:32b" if "claude" in provider_name or "gemini" in provider_name else "llama3:latest"
            provider = LLMProvider(provider="ollama", model=local_model)

        try:
            return Ok(await provider.invoke(prompt))
        except QuotaRejectedError as exc:
            logger.warning(
                "🚀 [HYPERSONIC JUMP] Local Quota (PULMONES) exhausted for %s. Zero-Wait Failover...",
                provider.provider_name,
            )
            return Err(str(exc))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.warning(
                    "🚀 [HYPERSONIC JUMP] Provider %s hit 429. Skipping immediately...",
                    provider.provider_name,
                )
            elif exc.response.status_code == 401:
                logger.error(
                    "🚫 [EVICTION] Provider %s hit 401 Unauthorized. Evicting...",
                    provider.provider_name,
                )
                self._evicted.add(provider.provider_name)
            return Err(str(exc))
        except Exception as exc:
            if "HTTP 401" in str(exc) or "401" in str(exc) or "invalid_api_key" in str(exc):
                logger.error(
                    "🚫 [EVICTION] Provider %s hit 401 Unauthorized. Evicting...",
                    provider.provider_name,
                )
                self._evicted.add(provider.provider_name)
            return Err(str(exc))

    def cascade_stats(self) -> dict[str, Any]:
        """Aggregated cascade metrics."""
        return self._telemetry.stats()

    def select_model_for_intent(self, intent: str) -> str | None:
        """Resolve the optimal model for the primary provider's intent."""
        try:
            from cortex.extensions.llm._presets import resolve_model

            return resolve_model(self._primary.provider_name, intent)
        except ImportError:
            return None

    @staticmethod
    def optimal_provider_order(
        intent: str,
        *,
        min_tier: str = "local",
        max_cost: str = "high",
    ) -> list[tuple[str, str]]:
        """Return (provider_name, model) pairs for an intent, cost-optimized."""
        try:
            from cortex.extensions.llm._presets import providers_for_intent

            return providers_for_intent(
                intent, min_tier=min_tier, max_cost=max_cost, sort_by="cost"
            )
        except ImportError:
            return []

    @staticmethod
    def frontier_order(intent: str) -> list[tuple[str, str]]:
        """Return frontier-tier providers for an intent, cheapest first."""
        try:
            from cortex.extensions.llm._presets import frontier_providers

            return frontier_providers(intent)
        except ImportError:
            return []
