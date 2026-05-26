"""CORTEX v5.0 — LLM Router.

Enrutador resiliente con routing determinista por intención.
Implementa Strategy + Circuit Breaker + ROP (Ω₂ Landauer split).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

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

    def _ordered_fallbacks(self, prompt: CortexPrompt | IntentProfile) -> list[BaseProvider]:
        """Ordena fallbacks: intent affinity → A-record → cost → tier."""
        from cortex.extensions.llm._models import ReasoningMode

        # If passed an IntentProfile directly, wrap it or extract intent
        if isinstance(prompt, IntentProfile):
            effective_intent = prompt
            reasoning_mode = None
            estimated_tokens = 0
            requires_frontier_coercion = False
        else:
            effective_intent = prompt.intent
            reasoning_mode = prompt.reasoning_mode

            # Estimate prompt tokens (heuristic: 1 token = 3 chars)
            system_instruction = getattr(prompt, "system_instruction", "") or ""
            working_memory = getattr(prompt, "working_memory", []) or []
            total_chars = len(system_instruction)
            for msg in working_memory:
                if isinstance(msg, dict) and "content" in msg:
                    total_chars += len(str(msg["content"]))
            estimated_tokens = (total_chars // 3) + (getattr(prompt, "max_tokens", 0) or 0)

            # Check for verification terms (frontier coercion constraint)
            prompt_text = system_instruction.lower()
            for msg in working_memory:
                if isinstance(msg, dict) and "content" in msg:
                    prompt_text += " " + str(msg["content"]).lower()
            requires_frontier_coercion = any(
                term in prompt_text for term in ["anvil", "z3", "formal", "verify"]
            )

        # Axiom Ω₁₆: If reasoning mode is DEEP_THINK, ULTRA_THINK, or DEEP_RESEARCH,
        # coerce the fallback intent to REASONING to select the right model map.
        if reasoning_mode in (
            ReasoningMode.DEEP_THINK,
            ReasoningMode.ULTRA_THINK,
            ReasoningMode.DEEP_RESEARCH,
        ):
            effective_intent = IntentProfile.REASONING

        typed_matches: list[BaseProvider] = []
        safety_net: list[BaseProvider] = []

        for p in self._fallbacks:
            if classify_tier(p, effective_intent) == CascadeTier.TYPED_MATCH:
                typed_matches.append(p)
            else:
                safety_net.append(p)

        # Axiom Ω₁₆: ULTRA_THINK strictly requires frontier models.
        if reasoning_mode == ReasoningMode.ULTRA_THINK:
            frontier_typed = [p for p in typed_matches if p.tier == "frontier"]
            frontier_safety = [p for p in safety_net if p.tier == "frontier"]
            if frontier_typed or frontier_safety:
                typed_matches = frontier_typed
                safety_net = frontier_safety
            # Else: Constraint relaxation (keep original typed_matches and safety_net)

        # Apply A-record promotion + cost/tier tiebreaking
        promoted_typed = self._promote_by_latency_then_cost(
            typed_matches,
            effective_intent,
            estimated_tokens=estimated_tokens,
            requires_frontier=requires_frontier_coercion,
        )
        promoted_safety = self._promote_by_latency_then_cost(
            safety_net,
            effective_intent,
            estimated_tokens=estimated_tokens,
            requires_frontier=requires_frontier_coercion,
        )

        return promoted_typed + promoted_safety

    def _promote_by_latency_then_cost(
        self,
        providers: list[BaseProvider],
        intent: IntentProfile,
        estimated_tokens: int = 0,
        requires_frontier: bool = False,
    ) -> list[BaseProvider]:
        """A-record first (by latency), unknowns by (cost, tier)."""
        from cortex.config import LLM_LOCAL_FIRST

        # Partition providers by context window fit to handle constraint
        fits_context: list[BaseProvider] = []
        overflows_context: list[BaseProvider] = []
        for p in providers:
            p_window = getattr(p, "context_window", 128000)
            if p_window and estimated_tokens > p_window:
                overflows_context.append(p)
            else:
                fits_context.append(p)

        def process_group(group: list[BaseProvider]) -> list[BaseProvider]:
            if not group:
                return []
            p_known = self._cascade.promote_known_good(group, intent)
            # promote_known_good: [known_good by latency] + [unknown]
            known_count = sum(1 for p in p_known if self._cascade.get_a_record(p.provider_name))
            known = p_known[:known_count]
            unknown = p_known[known_count:]

            # Dynamic tier order if local-first is active
            tier_order = self._TIER_ORDER.copy()
            if LLM_LOCAL_FIRST:
                tier_order["local"] = -1  # Promote above frontier (0)

            if requires_frontier:
                unknown.sort(
                    key=lambda p: (
                        p.tier != "frontier",
                        self._COST_ORDER.get(p.cost_class, 4),
                        tier_order.get(p.tier, 2),
                    )
                )
            else:
                unknown.sort(
                    key=lambda p: (
                        self._COST_ORDER.get(p.cost_class, 4),
                        tier_order.get(p.tier, 2),
                    )
                )
            return known + unknown

        return process_group(fits_context) + process_group(overflows_context)

    async def execute_hedged(self, prompt: CortexPrompt) -> Result[str, str] | None:
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
                    tier=CascadeTier.PRIMARY,
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

    # Default safety margin: keep prompts under 90% of model window.
    _CONTEXT_SAFETY_MARGIN: float = 0.90
    _COMPRESSED_TAIL_MESSAGES: int = 6

    @staticmethod
    def _compress_working_memory(
        messages: list[dict[str, str]],
        max_words: int,
        tail: int,
    ) -> list[dict[str, str]]:
        """Truncate working_memory if it exceeds the entropic safety threshold."""
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
        """Ejecuta inferencia con cascade determinista por intención."""
        # Dynamic threshold based on provider context window (Ω₁₃)
        model_window = self._primary.context_window or 32000  # pyright: ignore
        max_words = int((model_window * self._CONTEXT_SAFETY_MARGIN) * 0.75)

        prompt.working_memory = self._compress_working_memory(
            prompt.working_memory,
            max_words,
            self._COMPRESSED_TAIL_MESSAGES,
        )

        # Thermal Heat-Sink: coalesce identical concurrent requests (Ω₂)
        # Fast tuple hashing instead of slow f"{dict}" serialization
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
        except Exception as exc:  # noqa: BLE001
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
        """Dispatch a prompt with optional provider override (hint) and Dynamic Cache Routing.

        Enforces policy Ω₁₆ & Ω₂: targeted routing for belief-chain audits and cache affinity.
        """
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
                                "🔥 [CACHE-ROUTING] Affinity detected correctly in %s. Routing directly to maximize exergy (O(1)).",
                                hp,
                            )
                            break
            except ImportError:
                pass

        if not provider_hint or self._primary.provider_name == provider_hint:
            return await self.execute_resilient(prompt)

        # Provider Hint: temporarily swap priority for this request
        for p in self._fallbacks:
            if p.provider_name == provider_hint:
                # Use a temporary router view or just try this provider first
                logger.debug("🎯 [ROUTING] Overriding primary with hint: %s", provider_hint)
                res = await self._try_provider(p, prompt)
                if res.is_ok():
                    return res
                break  # Fall back to standard resilience if hint provider fails

        return await self.execute_resilient(prompt)

    async def execute_swarm(self, prompt: CortexPrompt) -> Result[str, str] | None:
        """Ω₂₁: Parallel Swarm Racing."""
        from cortex.extensions.llm._models import ReasoningMode

        fallbacks = self._ordered_fallbacks(prompt)
        swarm_peers = []

        reasoning_mode = getattr(prompt, "reasoning_mode", None)
        if (
            reasoning_mode == ReasoningMode.ULTRA_THINK
            and getattr(self._primary, "tier", None) != "frontier"
        ):
            pass  # Skip primary for ULTRA_THINK if not frontier
        else:
            swarm_peers.append(self._primary)

        swarm_peers.extend(fallbacks[:2])

        active_peers = [
            p for p in swarm_peers if not self._cascade.is_nxdomain_cached(p.provider_name)
        ]

        if len(active_peers) < 2:
            return None

        logger.info(
            "🚀 [Ω₂₁ SWARM RACE] Starting race between: %s", [p.provider_name for p in active_peers]
        )

        result_race, errors = await HedgedRequestStrategy.race(active_peers, prompt)
        if result_race:
            self._cascade.set_a_record(result_race.winner, result_race.latency_ms)
            self._telemetry.emit(
                CascadeEvent(
                    intent=prompt.intent,
                    resolved_by=result_race.winner,
                    project=prompt.project,
                    tier=CascadeTier.PRIMARY,
                    depth=1,
                    latency_ms=result_race.latency_ms,
                    errors=errors,
                )
            )
            return Ok(result_race.response)

        return None

    async def _execute_resilient_impl(self, prompt: CortexPrompt) -> Result[str, str]:
        """Core cascade logic."""
        from cortex.extensions.llm._models import ReasoningMode

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
        start = time.time()

        # Verify if primary provider is suitable for ULTRA_THINK
        reasoning_mode = getattr(prompt, "reasoning_mode", None)
        primary_valid = True

        # Axiom Ω₁₆: ULTRA_THINK strictly requires frontier models.
        if reasoning_mode == ReasoningMode.ULTRA_THINK:
            if getattr(self._primary, "tier", None) != "frontier":
                primary_valid = False

        if self._primary.provider_name in self._evicted:
            primary_valid = False

        errors = []
        if primary_valid:
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
            errors.append(f"Primary ({self._primary.provider_name}): {res_primary.error}")  # type: ignore[reportAttributeAccessIssue]
        else:
            if self._primary.provider_name in self._evicted:
                errors.append(f"Primary ({self._primary.provider_name}): Skipped (Evicted via 401)")
            else:
                errors.append(
                    f"Primary ({self._primary.provider_name}): "
                    "Skipped (ULTRA_THINK requires frontier tier)"
                )

        # Phase 2: Fallback cascade
        fallbacks = self._ordered_fallbacks(prompt)

        for i, provider in enumerate(fallbacks, start=2):
            if provider.provider_name in self._evicted:
                errors.append(f"{provider.provider_name}: Skip (Evicted via 401)")
                continue

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

            errors.append(f"{provider.provider_name}: {res_fb.error}")  # pyright: ignore
            self._cascade.set_nx_record(provider.provider_name)

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
        import httpx

        try:
            return Ok(await provider.invoke(prompt))
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
        except Exception as exc:  # noqa: BLE001
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
                intent,
                min_tier=min_tier,
                max_cost=max_cost,
                sort_by="cost",
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
