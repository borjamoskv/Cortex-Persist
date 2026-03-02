# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.3 — Sovereign LLM Routing (KETER-∞ ROP).

Abstracción arquitectónica para desvincular el motor de razonamiento
de proveedores específicos. Implementa Strategy + Circuit Breaker
con Railway Oriented Programming (Result monads) y routing determinista
por tipo de intención (IntentProfile).

Axioma: Ω₃ (Byzantine Default) — los fallbacks son ciudadanos de primera
clase con contratos explícitos. Un prompt de código jamás degrada a un
modelo generalista.

Cascade order:
    1. Primary (sin filtro de intención)
    2. Fallbacks con intent ∈ provider.intent_affinity   ← typed match
    3. Fallbacks restantes (safety net — nunca corta la resiliencia)

Hedged Requests (DNS-over-HTTPS pattern):
    Cuando el primary tiene hedging_peers configurados, CORTEX envía
    la misma query a N providers simultáneamente y toma la primera
    respuesta. Las tareas perdedoras se cancelan. Ω₂: desperdicio
    controlado < latencia. Google lo llama "hedged requests".

Architecture (Ω₂ Landauer split — 1372 → 6 cohesive modules):
    _models.py      — IntentProfile, CascadeTier, CascadeEvent,
                      HedgedResult, CortexPrompt, BaseProvider
    _cache.py       — NegativeCache (RFC 2308), PositiveCache (A-record)
    _hedging.py     — HedgedRequestStrategy (DNS-over-HTTPS)
    _pool.py        — ProviderMetrics, WeightedProviderPool (Anycast)
    _validation.py  — DriftSignal, IntentValidator (DNSSEC)
    router.py       — CortexLLMRouter (this file — orchestrator only)
"""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Sequence

from cortex.llm._cache import NegativeCache, PositiveCache  # noqa: F401
from cortex.llm._hedging import HedgedRequestStrategy  # noqa: F401
from cortex.llm._models import (  # noqa: F401
    BaseProvider,
    CascadeEvent,
    CascadeTier,
    CortexPrompt,
    HedgedResult,
    IntentProfile,
)
from cortex.llm._pool import ProviderMetrics as ProviderMetrics  # noqa: F401
from cortex.llm._pool import WeightedProviderPool
from cortex.llm._validation import DriftSignal, IntentValidator  # noqa: F401
from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.llm.router")


# ─── Re-exports for backward compatibility ─────────────────────────────────
# All public symbols were previously in this file. Zero breaking changes.

__all__ = [
    # From _models
    "BaseProvider",
    "CascadeEvent",
    "CascadeTier",
    "CortexPrompt",
    "HedgedResult",
    "IntentProfile",
    # From _cache
    "NegativeCache",
    "PositiveCache",
    # From _hedging
    "HedgedRequestStrategy",
    # From _pool
    "ProviderMetrics",
    "WeightedProviderPool",
    # From _validation
    "DriftSignal",
    "IntentValidator",
    # This file
    "CortexLLMRouter",
]


# ─── Router ────────────────────────────────────────────────────────────────


class CortexLLMRouter:
    """Enrutador resiliente con routing determinista por intención.

    Implementa Strategy + Circuit Breaker + ROP.

    Cascade order:
        1. Primary (sin filtro — siempre se intenta primero)
        2. Fallbacks elegibles para la intención del prompt (typed match)
        3. Fallbacks no elegibles (safety net — mantiene resiliencia total)

    Retorna Result[str, str] — nunca lanza excepciones al caller.
    """

    _CASCADE_HISTORY_CAP: int = 100
    _ENTROPY_ELEVATION_THRESHOLD: int = 3

    def __init__(
        self,
        primary: BaseProvider,
        fallbacks: Sequence[BaseProvider] | None = None,
        *,
        negative_ttl: float = 300.0,
        positive_ttl: float = 600.0,
        hedging_providers: Sequence[BaseProvider] | None = None,
    ) -> None:
        self._primary = primary
        self._fallbacks = list(fallbacks) if fallbacks else []
        self._negative_cache = NegativeCache(default_ttl=negative_ttl)
        self._positive_cache = PositiveCache(default_ttl=positive_ttl)
        self._hedging_providers = list(hedging_providers) if hedging_providers else []
        self._last_hedged_result: HedgedResult | None = None
        self._provider_pool = WeightedProviderPool()
        self._intent_validator = IntentValidator()
        self._drift_history: deque[DriftSignal] = deque(maxlen=100)
        self._drift_penalty_count: int = 0
        # Entropy telemetry
        self._session_primary_failures: int = 0
        self._cascade_history: deque[CascadeEvent] = deque(maxlen=self._CASCADE_HISTORY_CAP)
        self._entropy_elevation_count: int = 0

    @property
    def primary(self) -> BaseProvider:
        return self._primary

    @property
    def fallbacks(self) -> list[BaseProvider]:
        return self._fallbacks

    # ── Internal ──────────────────────────────────────────────────────────

    def _promote_known_good(
        self,
        providers: list[BaseProvider],
        intent: IntentProfile,
    ) -> list[BaseProvider]:
        """Within a tier, promote A-record cached providers to the front.

        Known-good providers (fresh A-record) are sorted by latency
        (fastest first). Unknown providers maintain their original order.
        This is the DNS A-record hot-path optimization.
        """
        intent_key = intent.value
        known_good_set = {name for name, _ in self._positive_cache.known_good_providers(intent_key)}

        if not known_good_set:
            return providers  # no A-records → no reordering

        promoted: list[BaseProvider] = []
        rest: list[BaseProvider] = []

        for p in providers:
            if p.provider_name in known_good_set:
                promoted.append(p)
            else:
                rest.append(p)

        if promoted:
            # Sort promoted by cached latency — fastest first
            promoted.sort(
                key=lambda p: (
                    self._positive_cache.get_latency(p.provider_name, intent_key) or float("inf")
                )
            )
            logger.debug(
                "A-record promoted: %s for intent=%s",
                [p.provider_name for p in promoted],
                intent_key,
            )

        return promoted + rest

    def _ordered_fallbacks(self, intent: IntentProfile) -> list[BaseProvider]:
        """Ordena los fallbacks por afinidad de intención + A-record promotion.

        Semántica:
        - El prompt usa GENERAL → sin filtro, cascade completo en orden de registro.
        - El prompt usa intent específico (CODE, REASONING, CREATIVE):
            * typed-match  → provider con el intent específico en su afinidad.
            * safety-net   → providers GENERAL o sin afinidad específica (van al final).

        Within each tier, providers with a fresh A-record (positive cache)
        are promoted to the front, sorted by latency (fastest first).

        Invariante: el safety-net nunca se elimina, solo se retrasa.
        """
        if intent is IntentProfile.GENERAL:
            return self._promote_known_good(list(self._fallbacks), intent)

        typed: list[BaseProvider] = []
        untyped: list[BaseProvider] = []

        for fb in self._fallbacks:
            affinity = fb.intent_affinity
            if intent in affinity:
                typed.append(fb)
            else:
                untyped.append(fb)

        # A-record promotion within each tier
        typed = self._promote_known_good(typed, intent)
        untyped = self._promote_known_good(untyped, intent)

        ordered = typed + untyped

        if typed:
            typed_names = [f.provider_name for f in typed]
            untyped_names = [f.provider_name for f in untyped]
            logger.debug(
                "Intent=%s | typed-match fallbacks=%s | safety-net=%s",
                intent.value,
                typed_names,
                untyped_names,
            )
        else:
            logger.debug(
                "Intent=%s | no typed-match fallbacks — using full cascade",
                intent.value,
            )

        return ordered

    def _adaptive_positive_ttl(self, provider_name: str) -> float:
        """Calculate A-record TTL based on historical success rate.
        Perfect provider = 100% of base TTL. Flaky provider = reduced TTL.
        """
        success_rate = self._provider_pool.get_success_rate(provider_name)
        return self._positive_cache._default_ttl * success_rate

    def _adaptive_negative_ttl(self, provider_name: str) -> float:
        """Calculate NXDOMAIN TTL based on historical success rate.
        Perfect provider = base TTL. Dead provider = 2x base TTL.
        """
        success_rate = self._provider_pool.get_success_rate(provider_name)
        return self._negative_cache._default_ttl * (2.0 - success_rate)

    # ── Public API ────────────────────────────────────────────────────────

    async def execute_hedged(self, prompt: CortexPrompt) -> Result[str, str] | None:
        """Attempt hedged (parallel) execution if peers are available.

        Returns Ok(response) if a hedging peer wins, None if hedging is
        not viable (no peers / all NXDOMAIN-cached), or falls through
        to let the sequential cascade handle it.

        DNS-over-HTTPS pattern: race-to-first, cancel losers.
        Axiom: Ω₂ + Ω₅.
        """
        if not self._hedging_providers:
            return None

        intent_key = prompt.intent.value

        # Build eligible pool: primary + hedging peers, minus NXDOMAIN-cached
        eligible: list[BaseProvider] = [self._primary]
        for hp in self._hedging_providers:
            if not self._negative_cache.is_suppressed(hp.provider_name, intent_key):
                eligible.append(hp)
            else:
                logger.debug(
                    "Hedge pool: %s excluded (NXDOMAIN-cached for %s)",
                    hp.provider_name,
                    intent_key,
                )

        # Need ≥2 providers for a race to be meaningful
        if len(eligible) < 2:
            logger.debug(
                "Hedging skipped: only %d eligible provider(s)",
                len(eligible),
            )
            return None

        hedged_result, errors = await HedgedRequestStrategy.race(eligible, prompt)

        if hedged_result is not None:
            self._last_hedged_result = hedged_result
            return Ok(hedged_result.response)

        # All hedging peers failed — record in negative cache
        # errors format: "provider_name: reason" (Ω₃: parse defensively)
        for error_msg in errors:
            provider_name = (error_msg.split(":", 1)[0] or "").strip()
            # Never suppress the primary (Byzantine Default) or malformed entries
            if not provider_name or provider_name == self._primary.provider_name:
                continue
            ttl = self._adaptive_negative_ttl(provider_name)
            self._negative_cache.record_failure(provider_name, intent_key, ttl=ttl)

        logger.debug(
            "Hedging failed for all %d providers — falling through to cascade",
            len(eligible),
        )
        return None

    async def execute_resilient(self, prompt: CortexPrompt) -> Result[str, str]:
        """Ejecuta inferencia con cascade determinista por intención.

        Ok(response) en éxito, Err(detail) si todos los proveedores fallan.

        Execution order:
            0. Hedged requests (if hedging_providers configured) — race-to-first
            1. Primary — sequential (NUNCA suprimido, Ω₃ Byzantine Default)
            2. Typed-match fallbacks
            3. Safety-net fallbacks

        RFC 2308 (Negative Caching):
            Fallbacks que fallaron recientemente son suprimidos durante su TTL.
            El primario NUNCA es suprimido (Ω₃ Byzantine Default).

        Emits a CascadeEvent after every call for entropy telemetry.
        """
        errors: list[str] = []
        intent_key = prompt.intent.value
        attempts = 0

        # 0. Hedged requests — DNS-over-HTTPS pattern
        hedged = await self.execute_hedged(prompt)
        if hedged is not None and isinstance(hedged, Ok):
            self._emit_cascade_event(
                prompt.intent,
                "hedged",
                CascadeTier.PRIMARY,
                1,
            )
            return hedged

        # 1. Primario — NUNCA suprimido (Byzantine Default: siempre verificar)
        attempts += 1
        start_primary = time.monotonic()
        result = await self._try_provider(self._primary, prompt)
        if isinstance(result, Ok):
            latency_ms = (time.monotonic() - start_primary) * 1000
            ttl = self._adaptive_positive_ttl(self._primary.provider_name)
            self._positive_cache.record_success(
                self._primary.provider_name, intent_key, latency_ms, ttl=ttl
            )
            self._session_primary_failures = 0  # streak broken
            self._emit_cascade_event(
                prompt.intent,
                self._primary.provider_name,
                CascadeTier.PRIMARY,
                attempts,
            )
            self._validate_and_penalize(self._primary.provider_name, result.value, prompt.intent)
            return result
        self._session_primary_failures += 1
        errors.append(f"{self._primary.provider_name}: {result.error}")

        # 2 + 3. Cascade: typed-match primero, safety-net después
        for fallback in self._ordered_fallbacks(prompt.intent):
            # RFC 2308: skip NXDOMAIN-cached providers
            if self._negative_cache.is_suppressed(fallback.provider_name, intent_key):
                logger.debug(
                    "NXDOMAIN skip: %s suppressed for intent=%s",
                    fallback.provider_name,
                    intent_key,
                )
                errors.append(f"{fallback.provider_name}: NXDOMAIN-cached")
                continue

            attempts += 1
            start_fb = time.monotonic()
            result = await self._try_provider(fallback, prompt)
            if isinstance(result, Ok):
                latency_ms = (time.monotonic() - start_fb) * 1000
                ttl = self._adaptive_positive_ttl(fallback.provider_name)
                self._positive_cache.record_success(
                    fallback.provider_name, intent_key, latency_ms, ttl=ttl
                )
                tier = self._classify_tier(fallback, prompt.intent)
                self._emit_cascade_event(
                    prompt.intent,
                    fallback.provider_name,
                    tier,
                    attempts,
                )
                self._validate_and_penalize(fallback.provider_name, result.value, prompt.intent)
                return result
            # Record failure → suppress for TTL, scoped by intent
            ttl = self._adaptive_negative_ttl(fallback.provider_name)
            self._negative_cache.record_failure(fallback.provider_name, intent_key, ttl=ttl)
            errors.append(f"{fallback.provider_name}: {result.error}")

        # Singularidad Negativa: todos fallaron
        self._emit_cascade_event(
            prompt.intent,
            None,
            CascadeTier.NONE,
            attempts,
        )
        detail = " | ".join(errors)
        logger.error("Singularidad Negativa [intent=%s]: %s", prompt.intent.value, detail)
        return Err(f"All providers failed: {detail}")

    async def _try_provider(self, provider: BaseProvider, prompt: CortexPrompt) -> Result[str, str]:
        """Try a single provider, returning Result. Records Anycast metrics."""
        start = time.monotonic()
        try:
            response = await provider.invoke(prompt)
            latency_ms = (time.monotonic() - start) * 1000
            self._provider_pool.record_success(provider.provider_name, latency_ms)
            return Ok(response)
        except Exception as e:  # deliberate boundary — LLM providers can raise any type
            latency_ms = (time.monotonic() - start) * 1000
            self._provider_pool.record_failure(provider.provider_name, latency_ms)
            logger.warning(
                "Provider '%s' failed [intent=%s, %.1fms]: %s",
                provider.provider_name,
                prompt.intent.value,
                latency_ms,
                e,
            )
            return Err(str(e))

    # ── Entropy Telemetry ─────────────────────────────────────────────────

    @staticmethod
    def _classify_tier(provider: BaseProvider, intent: IntentProfile) -> CascadeTier:
        """Classify which cascade tier a fallback belongs to.

        - typed-match:  provider declares the prompt's intent in its affinity
        - safety-net:   provider is GENERAL-only or from a different domain
        """
        if intent is IntentProfile.GENERAL:
            return CascadeTier.TYPED_MATCH  # GENERAL accepts all
        if intent in provider.intent_affinity:
            return CascadeTier.TYPED_MATCH
        return CascadeTier.SAFETY_NET

    def _emit_cascade_event(
        self,
        intent: IntentProfile,
        resolved_by: str | None,
        tier: CascadeTier,
        depth: int,
    ) -> None:
        """Record structured telemetry for this cascade resolution."""
        event = CascadeEvent(
            intent=intent,
            resolved_by=resolved_by,
            resolved_tier=tier,
            cascade_depth=depth,
            primary_consecutive_failures=self._session_primary_failures,
        )
        self._cascade_history.append(event)

        # Entropy elevation detection
        if (
            tier is CascadeTier.SAFETY_NET
            and self._session_primary_failures >= self._ENTROPY_ELEVATION_THRESHOLD
        ):
            self._entropy_elevation_count += 1
            logger.warning(
                "ENTROPY ELEVATION [intent=%s]: safety-net '%s' resolved after "
                "%d consecutive primary failures (depth=%d)",
                intent.value,
                resolved_by,
                self._session_primary_failures,
                depth,
            )
        else:
            logger.info(
                "CASCADE [intent=%s]: tier=%s provider=%s depth=%d primary_streak=%d",
                intent.value,
                tier.value,
                resolved_by or "NONE",
                depth,
                self._session_primary_failures,
            )

    @property
    def cascade_stats(self) -> dict[str, int]:
        """Observability: aggregated cascade metrics.

        Returns counts of how each tier resolved calls, plus the
        entropy elevation count (safety-net after ≥3 primary failures).
        """
        stats: dict[str, int] = {
            "total_calls": len(self._cascade_history),
            "primary_hits": 0,
            "typed_match_hits": 0,
            "safety_net_hits": 0,
            "none_hits": 0,
            "entropy_elevation_count": self._entropy_elevation_count,
            "current_primary_streak": self._session_primary_failures,
        }
        _TIER_KEY: dict[CascadeTier, str] = {
            CascadeTier.PRIMARY: "primary_hits",
            CascadeTier.TYPED_MATCH: "typed_match_hits",
            CascadeTier.SAFETY_NET: "safety_net_hits",
            CascadeTier.NONE: "none_hits",
        }
        for event in self._cascade_history:
            key = _TIER_KEY.get(event.resolved_tier)
            if key:
                stats[key] += 1
        return stats

    @property
    def cascade_history(self) -> list[CascadeEvent]:
        """Read-only snapshot of recent cascade events."""
        return list(self._cascade_history)

    # ── Cache & Aliases ───────────────────────────────────────────────────

    def clear_negative_cache(self) -> None:
        """Flush NXDOMAIN cache — use after config changes or manual override."""
        self._negative_cache.clear()
        logger.info("NXDOMAIN cache flushed")

    @property
    def negative_cache(self) -> NegativeCache:
        """Read-only access to the negative cache (observability)."""
        return self._negative_cache

    @property
    def last_hedged_result(self) -> HedgedResult | None:
        """Last hedged race result (observability/debugging)."""
        return self._last_hedged_result

    @property
    def hedging_providers(self) -> list[BaseProvider]:
        """Configured hedging peers."""
        return self._hedging_providers

    @property
    def provider_pool(self) -> WeightedProviderPool:
        """Anycast-style weighted provider pool (observability)."""
        return self._provider_pool

    @property
    def positive_cache(self) -> PositiveCache:
        """Read-only access to the positive cache (observability)."""
        return self._positive_cache

    def clear_positive_cache(self) -> None:
        """Flush A-record cache — use after config changes."""
        self._positive_cache.clear()
        logger.info("A-record cache flushed")

    def clear_caches(self) -> None:
        """Flush both NXDOMAIN and A-record caches."""
        self._negative_cache.clear()
        self._positive_cache.clear()
        logger.info("All resolver caches flushed (NXDOMAIN + A-record)")

    # ── DNSSEC Validation ─────────────────────────────────────────

    def _validate_and_penalize(
        self,
        provider_name: str,
        response: str,
        intent: IntentProfile,
    ) -> DriftSignal:
        """DNSSEC: validate response matches intent, penalize on drift.

        If drift is confirmed (confidence ≥ threshold), the provider's
        weight in the pool is penalized by recording a synthetic failure.
        This makes the provider less likely to be selected in future calls.

        The response is still returned to the caller — DNSSEC doesn't
        reject, it adjusts trust for future routing.
        """
        signal = self._intent_validator.validate(response, intent, provider_name)
        self._drift_history.append(signal)

        if signal.is_drift:
            self._drift_penalty_count += 1
            # Synthetic failure: apply weight penalty via the pool
            # Use a high latency (5000ms) to heavily penalize
            self._provider_pool.record_failure(provider_name, 5000.0)
            logger.warning(
                "DNSSEC DRIFT [%s]: %s (confidence=%.2f)",
                provider_name,
                signal.evidence,
                signal.confidence,
            )
        else:
            logger.debug(
                "DNSSEC OK [%s]: intent=%s confidence=%.2f",
                provider_name,
                intent.value,
                signal.confidence,
            )

        return signal

    @property
    def drift_history(self) -> list[DriftSignal]:
        """Read-only snapshot of recent DNSSEC validation signals."""
        return list(self._drift_history)

    @property
    def drift_stats(self) -> dict[str, int]:
        """Aggregated drift detection stats."""
        total = len(self._drift_history)
        drifts = sum(1 for s in self._drift_history if s.is_drift)
        return {
            "total_validations": total,
            "drift_detected": drifts,
            "drift_penalties_applied": self._drift_penalty_count,
            "clean_rate": round((total - drifts) / max(total, 1), 4),
        }

    async def invoke(self, prompt: CortexPrompt) -> Result[str, str]:
        """Primary entry point — alias for execute_resilient."""
        return await self.execute_resilient(prompt)
