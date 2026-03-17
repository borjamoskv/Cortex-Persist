from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from cortex.extensions.llm._cascade import CascadeManager, classify_tier
from cortex.extensions.llm._hedging import HedgedRequestStrategy
from cortex.extensions.llm._models import (
    BaseProvider,
    CascadeEvent,
    CascadeTier,
    CortexPrompt,
    HedgedResult,
    IntentProfile,
)
from cortex.extensions.llm._telemetry import CascadeTelemetry
from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.extensions.llm.router")

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
        fallbacks: Optional[Sequence[BaseProvider]] = None,
        *,
        negative_ttl: float = 300.0,
        positive_ttl: float = 600.0,
        hedging_providers: Optional[Sequence[BaseProvider]] = None,
        db_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self._primary = primary
        self._fallbacks = list(fallbacks or [])
        self._hedging_providers = list(hedging_providers or [])
        self._cascade = CascadeManager(negative_ttl, positive_ttl)
        self._telemetry = CascadeTelemetry(db_path=str(db_path) if db_path else None)
        # Thermal Heat-Sink: coalesce identical inflight prompts (Ω₂)
        self._inflight: dict[str, asyncio.Future[Result[str, str]]] = {}

    @property
    def primary(self) -> BaseProvider:
        return self._primary

    @property
    def fallbacks(self) -> list[BaseProvider]:
        return self._fallbacks

    # Cost class ordering for tiebreaking (cheaper first)
    _COST_ORDER: dict[str, int] = {
        "free": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "variable": 4,
    }

    # Tier ordering (higher quality first)
    _TIER_ORDER: dict[str, int] = {
        "frontier": 0,
        "high": 1,
        "local": 2,
    }

    def _ordered_fallbacks(
        self,
        intent: IntentProfile,
    ) -> list[BaseProvider]:
        """Ordena fallbacks: intent affinity → A-record → cost → tier.

        Within each tier, promotes known-good (A-record) by latency,
        then sorts unknowns by cost_class (cheaper first), then by
        tier (frontier > high > local) for same-cost tiebreaking.
        """
        typed_matches: list[BaseProvider] = []
        safety_net: list[BaseProvider] = []

        for p in self._fallbacks:
            if classify_tier(p, intent) == CascadeTier.TYPED_MATCH:
                typed_matches.append(p)
            else:
                safety_net.append(p)

        # Apply A-record promotion + cost/tier tiebreaking
        promoted_typed = self._promote_by_latency_then_cost(
            typed_matches,
            intent,
        )
        promoted_safety = self._promote_by_latency_then_cost(
            safety_net,
            intent,
        )

        return promoted_typed + promoted_safety

    def _promote_by_latency_then_cost(
        self,
        providers: list[BaseProvider],
        intent: IntentProfile,
    ) -> list[BaseProvider]:
        """A-record first (by latency), unknowns by (cost, tier)."""
        from cortex.config import LLM_LOCAL_FIRST

        p_known = self._cascade.promote_known_good(
            providers,
            intent,
        )
        # promote_known_good: [known_good by latency] + [unknown]
        known_count = sum(1 for p in p_known if self._cascade.get_a_record(p.provider_name))
        known = p_known[:known_count]
        unknown = p_known[known_count:]

        # Dynamic tier order if local-first is active
        tier_order = self._TIER_ORDER.copy()
        if LLM_LOCAL_FIRST:
            tier_order["local"] = -1  # Promote above frontier (0)

        unknown.sort(
            key=lambda p: (
                self._COST_ORDER.get(p.cost_class, 4),
                tier_order.get(p.tier, 2),
            )
        )
        return known + unknown

    async def execute_hedged(self, prompt: CortexPrompt) -> Optional[Result[str, str]]:
        """Attempt hedged (parallel) execution if peers are available."""
        if not self._hedging_providers:
            return None

        # Filter out circuit-broken/NXDOMAIN providers
        active_hedgers = [
            p
            for p in self._hedging_providers
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

    # ── Shannon Compression (Ω₁₃: Entropic Containment) ────────────

    # Maximum word count for working_memory before compression triggers.
    # ~32k words ≈ ~40k tokens — safety margin for most providers.
    _MAX_WORKING_MEMORY_WORDS: int = 32_000

    # After compression, keep the first message (instruction) and last N messages.
    _COMPRESSED_TAIL_MESSAGES: int = 6

    @staticmethod
    def _compress_working_memory(
        messages: list[dict[str, str]],
        max_words: int,
        tail: int,
    ) -> list[dict[str, str]]:
        """Truncate working_memory if it exceeds the entropic safety threshold.

        Preserves the first message (user instruction seed) and the last
        ``tail`` messages (recent context). Intermediate messages are replaced
        with a single compressed summary marker.

        Returns the original list unmodified if within budget.
        """
        total_words = sum(len(m.get("content", "").split()) for m in messages)
        if total_words <= max_words or len(messages) <= tail + 1:
            return messages

        head = messages[:1]
        compressed_marker = {
            "role": "system",
            "content": (
                f"[CORTEX Ω₁₃ Shannon Compression] "
                f"{len(messages) - 1 - tail} intermediate messages truncated "
                f"({total_words} words exceeded {max_words} word budget). "
                f"Only seed instruction and last {tail} messages retained."
            ),
        }
        recent = messages[-tail:]
        logger.warning(
            "🗜️ [SHANNON] Compressed working_memory: %d msgs (%d words) → %d msgs",
            len(messages),
            total_words,
            len(head) + 1 + len(recent),
        )
        return head + [compressed_marker] + recent

    async def execute_resilient(self, prompt: CortexPrompt) -> Result[str, str]:
        """Ejecuta inferencia con cascade determinista por intención.

        Kairos-Ω: Requests idénticos en vuelo se coalescan — O(1) en concurrencia.
        """
        # Ω₁₃ Shannon Compression: prevent quadratic token burn
        prompt.working_memory = self._compress_working_memory(
            prompt.working_memory,
            self._MAX_WORKING_MEMORY_WORDS,
            self._COMPRESSED_TAIL_MESSAGES,
        )

        # Thermal Heat-Sink: coalesce identical concurrent requests (Ω₂)
        prompt_key = hashlib.sha256(
            f"{prompt.system_instruction}:{prompt.working_memory}:{prompt.intent}".encode()
        ).hexdigest()

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
        except Exception as exc:  # noqa: BLE001
            if not future.done():
                future.set_exception(exc)
            raise
        finally:
            self._inflight.pop(prompt_key, None)

    async def invoke(self, prompt: CortexPrompt) -> Result[str, str]:
        """Alias for backward compatibility."""
        return await self.execute_resilient(prompt)

    async def _execute_resilient_impl(self, prompt: CortexPrompt) -> Result[str, str]:
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
        errors = [f"Primary ({self._primary.provider_name}): {res_primary.error}"]  # type: ignore[union-attr]

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

            errors.append(f"{provider.provider_name}: {res_fb.error}")  # type: ignore[union-attr]
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

    async def _try_provider(self, provider: BaseProvider, prompt: CortexPrompt) -> Result[str, str]:
        """Try a single provider, returning Result."""
        try:
            return Ok(await provider.invoke(prompt))
        except Exception as exc:  # noqa: BLE001
            return Err(str(exc))

    def cascade_stats(self) -> dict[str, Any]:
        """Aggregated cascade metrics."""
        return self._telemetry.stats()

    def select_model_for_intent(self, intent: str) -> Optional[str]:
        """Resolve the optimal model for the primary provider's intent.

        Uses the preset routing functions to find the best model
        based on the intent_model_map in llm_presets.json.
        """
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
        """Return (provider_name, model) pairs for an intent, cost-optimized.

        This is the bridge between preset metadata and runtime routing.
        Returns providers ordered by cost (cheapest first) filtered by tier.

        Usage:
            order = CortexLLMRouter.optimal_provider_order("code", max_cost="medium")
            # → [("groq", "llama-3.3-70b-versatile"), ("deepseek", "deepseek-chat"), ...]
        """
        try:
            from cortex.extensions.llm._presets import providers_for_intent

            return providers_for_intent(
                intent,
                min_tier=min_tier,
                max_cost=max_cost,
                sort_by="cost",
            )
        except ImportError:
            return []

    @staticmethod
    def frontier_order(intent: str) -> list[tuple[str, str]]:
        """Return frontier-tier providers for an intent, cheapest first.

        Convenience for high-stakes tasks where only frontier models are acceptable.
        """
        try:
            from cortex.extensions.llm._presets import frontier_providers

            return frontier_providers(intent)
        except ImportError:
            return []
