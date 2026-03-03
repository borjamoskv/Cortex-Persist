from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from cortex.llm._cascade import CascadeManager, classify_tier
from cortex.llm._hedging import HedgedRequestStrategy
from cortex.llm._models import (
    BaseProvider,
    CascadeEvent,
    CascadeTier,
    CortexPrompt,
    HedgedResult,
    IntentProfile,
)
from cortex.llm._telemetry import CascadeTelemetry
from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.llm.router")

# Re-exports for backward compatibility
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
    """Enrutador resiliente con routing determinista por intención.

    Implementa Strategy + Circuit Breaker + ROP (Ω₂ Landauer split).
    """

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
        self._inflight: dict[str, asyncio.Future[Result[str]]] = {}

    @property
    def primary(self) -> BaseProvider:
        return self._primary

    @property
    def fallbacks(self) -> list[BaseProvider]:
        return self._fallbacks

    def _ordered_fallbacks(self, intent: IntentProfile) -> list[BaseProvider]:
        """Ordena los fallbacks por afinidad de intención."""
        typed_matches: list[BaseProvider] = []
        safety_net: list[BaseProvider] = []

        for p in self._fallbacks:
            if classify_tier(p, intent) == CascadeTier.TYPED_MATCH:
                typed_matches.append(p)
            else:
                safety_net.append(p)

        # Apply A-record promotion (fastest first)
        promoted_typed = self._cascade.promote_known_good(typed_matches, intent)
        promoted_safety = self._cascade.promote_known_good(safety_net, intent)

        return promoted_typed + promoted_safety

    async def execute_hedged(self, prompt: CortexPrompt) -> Result[str] | None:
        """Attempt hedged (parallel) execution if peers are available."""
        if not self._hedging_providers:
            return None

        # Filter out circuit-broken/NXDOMAIN providers
        active_hedgers = [
            p for p in self._hedging_providers
            if not self._cascade.is_nxdomain_cached(p.provider_name)
        ]
        if not active_hedgers:
            return None

        result_hedge, errors = await HedgedRequestStrategy.race(active_hedgers, prompt)
        if result_hedge:
            # Winner found — cache A-record and return
            self._cascade.set_a_record(result_hedge.winner, result_hedge.latency_ms)
            self._telemetry.emit(
                CascadeEvent(
                    intent=prompt.intent,
                    resolved_by=result_hedge.winner,
                    project=prompt.project,
                    tier=CascadeTier.PRIMARY,  # Hedging is primary-tier
                    depth=1,
                    latency_ms=result_hedge.latency_ms,
                    errors=errors,
                )
            )
            return Ok(result_hedge.response)

        # All hedged requests failed — mark them as NXDOMAIN cached
        for p in active_hedgers:
            self._cascade.set_nx_record(p.provider_name)
        return None

    def clear_positive_cache(self) -> None:
        """Clear A-records."""
        self._cascade._a_records.clear()

    def clear_negative_cache(self) -> None:
        """Clear NXDOMAIN records."""
        self._cascade._nxdomain_cache.clear()

    async def execute_resilient(self, prompt: CortexPrompt) -> Result[str]:
        """Ejecuta inferencia con cascade determinista por intención.

        Kairos-Ω: Requests idénticos en vuelo se coalescan — O(1) en concurrencia.
        """
        # Thermal Heat-Sink: coalesce identical concurrent requests (Ω₂)
        prompt_key = hashlib.sha256(
            f"{prompt.system_instruction}:{prompt.working_memory}:{prompt.intent}".encode()
        ).hexdigest()

        if prompt_key in self._inflight:
            logger.debug("🔥 [HEAT-SINK] Coalescing duplicate inflight prompt: %s...", prompt_key[:8])
            return await self._inflight[prompt_key]

        loop = asyncio.get_running_loop()
        future: asyncio.Future[Result[str]] = loop.create_future()
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

    async def invoke(self, prompt: CortexPrompt) -> Result[str]:
        """Alias for backward compatibility."""
        return await self.execute_resilient(prompt)

    async def _execute_resilient_impl(self, prompt: CortexPrompt) -> Result[str]:
        """Core cascade logic (extracted for Heat-Sink wrapping)."""
        # Phase 0: Hedging (Parallel race-to-first)
        hedged_res = await self.execute_hedged(prompt)
        if hedged_res:
            return hedged_res

        # Phase 1: Primary sequential attempt
        start = time.time()
        res_primary = await self._try_provider(self._primary, prompt)
        latency = (time.time() - start) * 1000

        if res_primary.is_ok():
            self._telemetry.emit(
                CascadeEvent(
                    intent=prompt.intent,
                    resolved_by=self._primary.provider_name,
                    project=prompt.project,
                    tier=CascadeTier.PRIMARY,
                    depth=1,
                    latency_ms=latency,
                )
            )
            return res_primary

        # Phase 2: Fallback cascade
        fallbacks = self._ordered_fallbacks(prompt.intent)
        errors = [f"Primary ({self._primary.provider_name}): {res_primary.error}"]

        for i, provider in enumerate(fallbacks, start=2):
            if self._cascade.is_nxdomain_cached(provider.provider_name):
                errors.append(f"{provider.provider_name}: Skip (NXDOMAIN cached)")
                continue

            fb_start = time.time()
            res_fb = await self._try_provider(provider, prompt)
            fb_latency = (time.time() - fb_start) * 1000

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
                    )
                )
                return res_fb

            errors.append(f"{provider.provider_name}: {res_fb.error}")
            self._cascade.set_nx_record(provider.provider_name)

        # Final defeat: record terminal event
        self._telemetry.emit(
            CascadeEvent(
                intent=prompt.intent,
                resolved_by=None,
                project=prompt.project,
                tier=CascadeTier.NONE,
                depth=len(fallbacks) + 1,
                latency_ms=(time.time() - start) * 1000,
                errors=errors,
            )
        )
        return Err(f"All providers failed. Cascade exhausted. Errors: {'; '.join(errors)}")

    async def _try_provider(self, provider: BaseProvider, prompt: CortexPrompt) -> Result[str]:
        """Try a single provider, returning Result."""
        try:
            return Ok(await provider.invoke(prompt))
        except Exception as exc:
            return Err(str(exc))

    def cascade_stats(self) -> dict[str, Any]:
        """Aggregated cascade metrics."""
        return self._telemetry.stats()
