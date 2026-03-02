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
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.llm.router")


# ─── Intent Classification ─────────────────────────────────────────────────


class IntentProfile(str, Enum):
    """Clasificación soberana de la intención del prompt.

    Permite al router seleccionar fallbacks con afinidad semántica,
    evitando que el ruido del error se propague entre dominios.
    """

    CODE = "code"
    """Generación, refactoring, debugging o análisis de código."""

    REASONING = "reasoning"
    """Análisis multi-paso, matemáticas, planificación estructurada."""

    CREATIVE = "creative"
    """Escritura, brainstorming, contenido narrativo."""

    GENERAL = "general"
    """Intención genérica o no clasificada — sin restricción de fallback."""


class CascadeTier(str, Enum):
    """Classification of which cascade tier resolved the call."""

    PRIMARY = "primary"
    TYPED_MATCH = "typed-match"
    SAFETY_NET = "safety-net"
    NONE = "none"  # all providers failed


@dataclass(frozen=True, slots=True)
class CascadeEvent:
    """Structured trace for a single execute_resilient call.

    Enables production measurement of entropy delta:
    - typed-match = entropy-neutral (domain preserved)
    - safety-net  = entropy-elevated (domain crossed)
    """

    intent: IntentProfile
    resolved_by: str | None
    resolved_tier: CascadeTier
    cascade_depth: int  # how many providers attempted before success
    primary_consecutive_failures: int  # session counter at call time
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(frozen=True, slots=True)
class HedgedResult:
    """Observability payload for hedged request races.

    Captures which provider won, response latency, and which providers
    were cancelled. Essential for tuning hedging_peers configuration.
    """

    winner: str
    """provider_name of the winning provider."""

    response: str
    """Response content from the winner."""

    latency_ms: float
    """Wall-clock latency of the winning provider (ms)."""

    cancelled: tuple[str, ...] = ()
    """provider_names of cancelled (loser) providers."""


# ─── Prompt ────────────────────────────────────────────────────────────────


class CortexPrompt(BaseModel):
    """Representación Soberana de una instrucción para el enjambre.
    Independiente del proveedor final (OpenAI, Anthropic, Gemini, etc).
    """

    system_instruction: str = Field(
        default="You are a helpful assistant.",
        description="El prompt del sistema o rol principal.",
    )
    working_memory: list[dict[str, str]] = Field(
        default_factory=list,
        description="Historial reciente o contexto de trabajo (rol/contenido).",
    )
    episodic_context: list[dict[str, str]] | None = Field(
        default=None,
        description="Recuerdos comprimidos o contexto a largo plazo recuperado.",
    )
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    intent: IntentProfile = Field(
        default=IntentProfile.GENERAL,
        description=(
            "Tipo de intención del prompt. Determina qué fallbacks son "
            "elegibles para el cascade determinista. GENERAL usa todos."
        ),
    )

    def to_openai_messages(self) -> list[dict[str, str]]:
        """Convierte la estructura soberana al formato de mensajes de OpenAI."""
        messages: list[dict[str, str]] = [{"role": "system", "content": self.system_instruction}]

        # Inyectar contexto episódico si existe, asimilado tempranamente
        if self.episodic_context:
            context_str = "\n".join(
                f"[{m.get('role', 'memory')}]: {m.get('content', '')}"
                for m in self.episodic_context
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"<episodic_context>\n{context_str}\n</episodic_context>\n"
                        "Use this context for the following interactions if relevant."
                    ),
                }
            )

        messages.extend(self.working_memory)
        return messages


# ─── Provider Interface ────────────────────────────────────────────────────


class BaseProvider(ABC):
    """Interfaz estricta que todo proveedor LLM debe cumplir.

    Cada provider declara su `intent_affinity` — el conjunto de intenciones
    que sirve con alta precisión. El router usa esta declaración para
    construir el cascade determinista.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identificador único del proveedor."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nombre del modelo subyacente."""
        ...

    @property
    def intent_affinity(self) -> frozenset[IntentProfile]:
        """Intenciones para las que este provider es adecuado.

        Override en subclases especializadas. Por defecto, GENERAL (sin restricción).
        Esto preserva la compatibilidad con providers existentes: un provider
        sin override se comporta exactamente igual que antes.
        """
        return frozenset({IntentProfile.GENERAL})

    @abstractmethod
    async def invoke(self, prompt: CortexPrompt) -> str:
        """Traduce el CortexPrompt al formato nativo del LLM y ejecuta la inferencia."""
        ...


# ─── Negative Cache (RFC 2308) ─────────────────────────────────────────────


class NegativeCache:
    """RFC 2308 NXDOMAIN cache for failed providers.

    When a provider fails for a specific intent, cache the failure with a TTL
    so subsequent calls skip it entirely. Converts the fallback cascade from
    reactive (try → fail → retry next call) to predictive (known-dead → skip).

    Key: (provider_name, intent_value) — scoped per intent, not global.
    A provider that fails for CODE may still be healthy for REASONING.

    Axiom: Ω₅ (Antifragile by Default) — the failure feeds the system.
    """

    __slots__ = ("_entries", "_default_ttl")

    def __init__(self, default_ttl: float = 300.0) -> None:
        self._entries: dict[tuple[str, str], float] = {}
        self._default_ttl = default_ttl  # 5 min default

    def record_failure(
        self, provider_name: str, intent: str, ttl: float | None = None
    ) -> None:
        """NXDOMAIN — cache that this provider failed for this intent."""
        expiry = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        self._entries[(provider_name, intent)] = expiry
        logger.debug(
            "NXDOMAIN cached: %s for intent=%s (TTL=%.0fs)",
            provider_name,
            intent,
            ttl if ttl is not None else self._default_ttl,
        )

    def is_suppressed(self, provider_name: str, intent: str) -> bool:
        """Check if provider is in the NXDOMAIN cache (still within TTL)."""
        key = (provider_name, intent)
        expiry = self._entries.get(key)
        if expiry is None:
            return False
        if time.monotonic() >= expiry:
            del self._entries[key]  # TTL expired — resurrect
            logger.debug(
                "NXDOMAIN expired: %s resurrected for intent=%s",
                provider_name,
                intent,
            )
            return False
        return True

    def clear(self) -> None:
        """Flush all negative cache entries."""
        self._entries.clear()

    @property
    def suppressed_count(self) -> int:
        """Active suppressions count (for observability)."""
        return len(self._entries)


class PositiveCache:
    """DNS A-Record cache for successful providers.

    Symmetric counterpart to NegativeCache (NXDOMAIN).
    Key: (provider_name, intent_value) — scoped per intent.
    Value: (expiry_timestamp, latency_ms).

    Providers with a fresh A-record get promoted in the cascade
    ordering via ``known_good_providers(intent)``. Among known-good
    providers, faster ones (lower latency) come first.

    TTL default = 600s (10 min) — 2x longer than NXDOMAIN, matching
    typical DNS behavior: positive evidence is more durable than negative.

    Axiom: Ω₅ (Antifragile by Default) — success feeds the system.
    """

    __slots__ = ("_entries", "_default_ttl")

    def __init__(self, default_ttl: float = 600.0) -> None:
        self._entries: dict[tuple[str, str], tuple[float, float]] = {}
        self._default_ttl = default_ttl  # 10 min default

    def record_success(
        self,
        provider_name: str,
        intent: str,
        latency_ms: float,
        ttl: float | None = None,
    ) -> None:
        """A-record — cache that this provider succeeded for this intent."""
        expiry = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        self._entries[(provider_name, intent)] = (expiry, latency_ms)
        logger.debug(
            "A-record cached: %s for intent=%s (%.1fms, TTL=%.0fs)",
            provider_name,
            intent,
            latency_ms,
            ttl if ttl is not None else self._default_ttl,
        )

    def is_known_good(self, provider_name: str, intent: str) -> bool:
        """Check if provider has a valid A-record for this intent."""
        key = (provider_name, intent)
        entry = self._entries.get(key)
        if entry is None:
            return False
        expiry, _ = entry
        if time.monotonic() >= expiry:
            del self._entries[key]  # TTL expired
            return False
        return True

    def get_latency(self, provider_name: str, intent: str) -> float | None:
        """Get cached latency for a known-good provider, or None."""
        key = (provider_name, intent)
        entry = self._entries.get(key)
        if entry is None:
            return None
        expiry, latency_ms = entry
        if time.monotonic() >= expiry:
            del self._entries[key]
            return None
        return latency_ms

    def known_good_providers(self, intent: str) -> list[tuple[str, float]]:
        """Return all known-good providers for an intent, sorted by latency.

        Returns list of (provider_name, latency_ms) — fastest first.
        Expired entries are cleaned lazily during iteration.
        """
        now = time.monotonic()
        expired_keys: list[tuple[str, str]] = []
        good: list[tuple[str, float]] = []

        for (pname, pintent), (expiry, latency) in self._entries.items():
            if pintent != intent:
                continue
            if now >= expiry:
                expired_keys.append((pname, pintent))
                continue
            good.append((pname, latency))

        # Lazy cleanup
        for key in expired_keys:
            del self._entries[key]

        # Sort by latency — fastest first
        good.sort(key=lambda x: x[1])
        return good

    def clear(self) -> None:
        """Flush all positive cache entries."""
        self._entries.clear()

    @property
    def cached_count(self) -> int:
        """Active A-record count (for observability)."""
        return len(self._entries)


# ─── Hedged Requests (DNS-over-HTTPS) ──────────────────────────────────────


class HedgedRequestStrategy:
    """DNS-over-HTTPS inspired race-to-first execution.

    Sends the same query to N providers simultaneously via
    ``asyncio.wait(FIRST_COMPLETED)``. Takes the first Ok response,
    cancels the rest. If all fail, returns the collected errors so
    the caller can fall through to the sequential cascade.

    Axiom: Ω₂ (controlled waste < latency) + Ω₅ (redundancy as fuel).
    """

    @staticmethod
    async def race(
        providers: list[BaseProvider],
        prompt: CortexPrompt,
    ) -> tuple[HedgedResult | None, list[str]]:
        """Race providers. Returns (HedgedResult | None, errors).

        If a provider wins, HedgedResult is populated and errors is empty.
        If all fail, HedgedResult is None and errors contains all failures.
        """
        if not providers:
            return None, ["No providers for hedging"]

        start = time.monotonic()

        # Create named tasks for traceability
        tasks: dict[asyncio.Task[str], BaseProvider] = {}
        for p in providers:
            task = asyncio.create_task(
                p.invoke(prompt),
                name=f"hedge:{p.provider_name}",
            )
            tasks[task] = p

        pending = set(tasks.keys())
        errors: list[str] = []
        result: HedgedResult | None = None

        try:
            while pending:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                for completed in done:
                    provider = tasks[completed]
                    exc = completed.exception()
                    if exc is not None:
                        errors.append(f"{provider.provider_name}: {exc}")
                        logger.debug(
                            "Hedge loser (error): %s — %s",
                            provider.provider_name,
                            exc,
                        )
                        continue

                    # Winner found — cancel remaining
                    latency_ms = (time.monotonic() - start) * 1000
                    cancelled_names: list[str] = []
                    for p_task in pending:
                        p_task.cancel()
                        cancelled_names.append(tasks[p_task].provider_name)

                    result = HedgedResult(
                        winner=provider.provider_name,
                        response=completed.result(),
                        latency_ms=latency_ms,
                        cancelled=tuple(cancelled_names),
                    )

                    logger.info(
                        "Hedge winner: %s (%.1fms) | cancelled: %s",
                        result.winner,
                        result.latency_ms,
                        cancelled_names or "none",
                    )

                    # Await cancelled tasks to suppress warnings
                    for p_task in pending:
                        try:
                            await p_task
                        except (asyncio.CancelledError, Exception):
                            pass

                    return result, []

        except Exception as e:
            # Cleanup on unexpected error
            for t in pending:
                t.cancel()
            errors.append(f"Hedging infrastructure: {e}")

        return result, errors


# ─── Provider Metrics (Anycast) ────────────────────────────────────────────


@dataclass(slots=True)
class ProviderMetrics:
    """EWMA-based latency and success tracking per provider.

    DNS Anycast routes to the nearest (fastest) server. CORTEX does the
    same at the semantic level: providers that respond faster accumulate
    higher weight and get more traffic.

    Uses Exponentially Weighted Moving Average (EWMA) for latency with
    α=0.3 (recent observations bias). Success rate is a simple ratio.

    Axiom: Ω₅ (Antifragile) — metrics feed the system, not just report.
    """

    total_calls: int = 0
    total_successes: int = 0
    total_failures: int = 0
    ewma_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    last_latency_ms: float = 0.0

    _EWMA_ALPHA: float = field(default=0.3, repr=False)

    def record_success(self, latency_ms: float) -> None:
        """Record a successful call with its latency."""
        self.total_calls += 1
        self.total_successes += 1
        self._update_latency(latency_ms)

    def record_failure(self, latency_ms: float) -> None:
        """Record a failed call with its latency."""
        self.total_calls += 1
        self.total_failures += 1
        self._update_latency(latency_ms)

    def _update_latency(self, latency_ms: float) -> None:
        """Update EWMA and extrema."""
        self.last_latency_ms = latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)

        if self.total_calls == 1:
            self.ewma_latency_ms = latency_ms
        else:
            alpha = self._EWMA_ALPHA
            self.ewma_latency_ms = (
                alpha * latency_ms + (1 - alpha) * self.ewma_latency_ms
            )

    @property
    def success_rate(self) -> float:
        """Success ratio [0.0, 1.0]. Returns 1.0 if no calls yet."""
        if self.total_calls == 0:
            return 1.0
        return self.total_successes / self.total_calls

    @property
    def weight(self) -> float:
        """Routing weight: inversely proportional to EWMA latency.

        Faster providers get higher weight. Failed providers get penalized
        by the success_rate multiplier (0.0 = always fails → weight 0).

        Weight = success_rate / max(ewma_latency_ms, 1.0)

        This produces a natural ranking where a provider at 100ms with
        100% success has 10x the weight of one at 1000ms with 100% success.
        """
        if self.total_calls == 0:
            return 1.0  # equal chance until observed
        return self.success_rate / max(self.ewma_latency_ms, 1.0)


class WeightedProviderPool:
    """DNS Anycast-style weighted provider pool.

    Same interface (BaseProvider), multiple backends. Routing by observed
    latency and success rate, using EWMA. Faster providers accumulate
    higher weight and get selected more often.

    Axiom: Ω₂ (entropic cost → route to lowest-cost provider) +
           Ω₅ (metrics anti-fragility → self-optimizing).
    """

    def __init__(self) -> None:
        self._metrics: dict[str, ProviderMetrics] = {}

    def get_or_create(self, provider_name: str) -> ProviderMetrics:
        """Get metrics for a provider, creating if new."""
        if provider_name not in self._metrics:
            self._metrics[provider_name] = ProviderMetrics()
        return self._metrics[provider_name]

    def record_success(self, provider_name: str, latency_ms: float) -> None:
        """Record a successful provider call."""
        self.get_or_create(provider_name).record_success(latency_ms)

    def record_failure(self, provider_name: str, latency_ms: float) -> None:
        """Record a failed provider call."""
        self.get_or_create(provider_name).record_failure(latency_ms)

    def select_weighted(self, providers: list[BaseProvider]) -> BaseProvider:
        """Select a provider weighted by inverse EWMA latency.

        Providers with no history get weight 1.0 (benefit of the doubt).
        Selection is deterministic: always picks the highest-weight provider.
        For probabilistic selection, use select_weighted_random().
        """
        if not providers:
            raise ValueError("No providers to select from")
        if len(providers) == 1:
            return providers[0]

        best = providers[0]
        best_weight = self.get_or_create(best.provider_name).weight
        for p in providers[1:]:
            w = self.get_or_create(p.provider_name).weight
            if w > best_weight:
                best = p
                best_weight = w

        logger.debug(
            "Anycast selected: %s (weight=%.6f)",
            best.provider_name,
            best_weight,
        )
        return best

    def rank(self, providers: list[BaseProvider]) -> list[BaseProvider]:
        """Sort providers by weight (highest first).

        Enables weight-aware cascade ordering: the router tries the
        historically fastest provider first, falling back down the ranking.
        """
        return sorted(
            providers,
            key=lambda p: self.get_or_create(p.provider_name).weight,
            reverse=True,
        )

    def snapshot(self) -> dict[str, dict[str, float]]:
        """Observability: current metrics for all tracked providers."""
        return {
            name: {
                "ewma_latency_ms": round(m.ewma_latency_ms, 2),
                "success_rate": round(m.success_rate, 4),
                "weight": round(m.weight, 6),
                "total_calls": m.total_calls,
            }
            for name, m in self._metrics.items()
        }

    def clear(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()


# ─── DNSSEC (Intent Validation) ────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DriftSignal:
    """DNSSEC validation result for a single response.

    Captures whether the response matched the requested intent,
    with confidence scoring and drift evidence.
    """

    provider: str
    """Provider that generated the response."""

    requested_intent: IntentProfile
    """What the prompt asked for."""

    detected_intent: IntentProfile
    """What the response actually looks like."""

    confidence: float
    """Detection confidence [0.0, 1.0]."""

    is_drift: bool
    """True if detected != requested and confidence > threshold."""

    evidence: str
    """Human-readable explanation of why drift was/wasn’t detected."""

    timestamp: float = field(default_factory=time.monotonic)


class IntentValidator:
    """DNSSEC for LLM routing — post-response intent verification.

    Validates that a provider’s response actually matches the requested
    intent. Uses heuristic signal detection (no LLM call required —
    zero-cost validation).

    DNS analogy:
        DNSSEC validates that the DNS response came from the authoritative
        server and wasn’t tampered with. IntentValidator validates that the
        LLM response matches the semantic domain of the request.

    Drift detection signals:
        CODE: code fences, function defs, imports, syntax patterns
        REASONING: numbered steps, logical connectors, QED markers
        CREATIVE: narrative structure, dialogue, metaphors
        GENERAL: no strong signal (always passes)

    Axiom: Ω₃ (Byzantine Default) — verify, then trust. Never reversed.
    """

    # Minimum response length to attempt validation
    _MIN_VALIDATION_LENGTH: int = 50

    # Confidence threshold for flagging drift
    _DRIFT_CONFIDENCE_THRESHOLD: float = 0.6

    # ── Signal patterns (compiled once) ─────────────────────────────

    _CODE_SIGNALS: tuple[re.Pattern[str], ...] = (
        re.compile(r"```\w*\n"),            # code fences
        re.compile(r"\bdef \w+\("),          # function defs
        re.compile(r"\bclass \w+[:(]"),      # class defs
        re.compile(r"\bimport \w+"),         # imports
        re.compile(r"\breturn \w+"),         # return statements
        re.compile(r"[{;}]\s*$", re.M),     # braces/semicolons
        re.compile(r"\b(if|for|while)\s*\("),  # control flow
        re.compile(r"=>|->|::\s*\w+"),       # arrows/type annotations
    )

    _REASONING_SIGNALS: tuple[re.Pattern[str], ...] = (
        re.compile(r"^\d+\.\s", re.M),       # numbered steps
        re.compile(r"\b(therefore|hence|thus|consequently|because|since)\b", re.I),
        re.compile(r"\b(first|second|third|finally|in conclusion)\b", re.I),
        re.compile(r"\b(analysis|hypothesis|evidence|conclusion|reasoning)\b", re.I),
        re.compile(r"\b(if .+ then)\b", re.I),  # conditional logic
        re.compile(r"[\+\-\*/=<>].*[\+\-\*/=<>]"),  # mathematical ops
    )

    _CREATIVE_SIGNALS: tuple[re.Pattern[str], ...] = (
        re.compile(r'["\u201c\u201d].{10,}["\u201c\u201d]'),  # dialogue
        re.compile(r"\b(once upon|story|narrative|imagine|dream)\b", re.I),
        re.compile(r"\b(metaphor|simile|poetry|verse|stanza)\b", re.I),
        re.compile(r"\b(chapter|scene|act|protagonist|character)\b", re.I),
        re.compile(r"[!]{2,}"),              # emphatic punctuation
        re.compile(r"\b(felt|whispered|sighed|gazed|wandered)\b", re.I),
    )

    def validate(
        self,
        response: str,
        requested_intent: IntentProfile,
        provider_name: str,
    ) -> DriftSignal:
        """Validate that a response matches the requested intent.

        Returns a DriftSignal with detection results. GENERAL intent
        always passes (no signal required).
        """
        # GENERAL never drifts — it accepts everything
        if requested_intent is IntentProfile.GENERAL:
            return DriftSignal(
                provider=provider_name,
                requested_intent=requested_intent,
                detected_intent=IntentProfile.GENERAL,
                confidence=1.0,
                is_drift=False,
                evidence="GENERAL intent — no validation required",
            )

        # Too short to validate meaningfully
        if len(response) < self._MIN_VALIDATION_LENGTH:
            return DriftSignal(
                provider=provider_name,
                requested_intent=requested_intent,
                detected_intent=requested_intent,  # benefit of the doubt
                confidence=0.0,
                is_drift=False,
                evidence=f"Response too short ({len(response)} chars) for validation",
            )

        # Score each domain
        scores = {
            IntentProfile.CODE: self._score(response, self._CODE_SIGNALS),
            IntentProfile.REASONING: self._score(response, self._REASONING_SIGNALS),
            IntentProfile.CREATIVE: self._score(response, self._CREATIVE_SIGNALS),
        }

        # Detected intent = highest scoring domain
        detected = max(scores, key=lambda k: scores[k])
        detected_score = scores[detected]
        requested_score = scores.get(requested_intent, 0.0)

        # Confidence: how much stronger is the detected signal vs requested
        if detected_score == 0.0:
            # No signals at all — can’t determine, benefit of the doubt
            return DriftSignal(
                provider=provider_name,
                requested_intent=requested_intent,
                detected_intent=requested_intent,
                confidence=0.0,
                is_drift=False,
                evidence="No domain signals detected",
            )

        if detected == requested_intent:
            return DriftSignal(
                provider=provider_name,
                requested_intent=requested_intent,
                detected_intent=detected,
                confidence=detected_score,
                is_drift=False,
                evidence=f"Matched: {detected.value} score={detected_score:.2f}",
            )

        # Drift detected — response doesn’t match requested intent
        drift_confidence = detected_score - requested_score
        is_drift = drift_confidence >= self._DRIFT_CONFIDENCE_THRESHOLD

        return DriftSignal(
            provider=provider_name,
            requested_intent=requested_intent,
            detected_intent=detected,
            confidence=drift_confidence,
            is_drift=is_drift,
            evidence=(
                f"Drift: requested={requested_intent.value}(score={requested_score:.2f}) "
                f"but detected={detected.value}(score={detected_score:.2f}) "
                f"delta={drift_confidence:.2f}"
            ),
        )

    @staticmethod
    def _score(text: str, patterns: tuple[re.Pattern[str], ...]) -> float:
        """Score how strongly text matches a set of signal patterns.

        Returns [0.0, 1.0] where 1.0 = all patterns matched.
        """
        if not patterns:
            return 0.0
        matches = sum(1 for p in patterns if p.search(text))
        return matches / len(patterns)


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
        self._cascade_history: deque[CascadeEvent] = deque(
            maxlen=self._CASCADE_HISTORY_CAP
        )
        self._entropy_elevation_count: int = 0

    @property
    def primary(self) -> BaseProvider:
        return self._primary

    @property
    def fallbacks(self) -> list[BaseProvider]:
        return self._fallbacks

    # ── Internal ──────────────────────────────────────────────────────────

    def _promote_known_good(
        self, providers: list[BaseProvider], intent: IntentProfile,
    ) -> list[BaseProvider]:
        """Within a tier, promote A-record cached providers to the front.

        Known-good providers (fresh A-record) are sorted by latency
        (fastest first). Unknown providers maintain their original order.
        This is the DNS A-record hot-path optimization.
        """
        intent_key = intent.value
        known_good_set = {
            name
            for name, _ in self._positive_cache.known_good_providers(intent_key)
        }

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
                key=lambda p: self._positive_cache.get_latency(
                    p.provider_name, intent_key
                )
                or float("inf")
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

    # ── Public API ────────────────────────────────────────────────────────

    async def execute_hedged(
        self, prompt: CortexPrompt
    ) -> Result[str, str] | None:
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
            if not self._negative_cache.is_suppressed(
                hp.provider_name, intent_key
            ):
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

        hedged_result, errors = await HedgedRequestStrategy.race(
            eligible, prompt
        )

        if hedged_result is not None:
            self._last_hedged_result = hedged_result
            return Ok(hedged_result.response)

        # All hedging peers failed — record in negative cache
        for error_msg in errors:
            provider_name = error_msg.split(":", 1)[0].strip()
            # Don't cache primary failures (Ω₃ Byzantine Default)
            if provider_name != self._primary.provider_name:
                self._negative_cache.record_failure(provider_name, intent_key)

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
                prompt.intent, "hedged", CascadeTier.PRIMARY, 1,
            )
            return hedged

        # 1. Primario — NUNCA suprimido (Byzantine Default: siempre verificar)
        attempts += 1
        start_primary = time.monotonic()
        result = await self._try_provider(self._primary, prompt)
        if isinstance(result, Ok):
            latency_ms = (time.monotonic() - start_primary) * 1000
            self._positive_cache.record_success(
                self._primary.provider_name, intent_key, latency_ms
            )
            self._session_primary_failures = 0  # streak broken
            self._emit_cascade_event(
                prompt.intent, self._primary.provider_name,
                CascadeTier.PRIMARY, attempts,
            )
            self._validate_and_penalize(
                self._primary.provider_name, result.value, prompt.intent
            )
            return result
        self._session_primary_failures += 1
        errors.append(f"{self._primary.provider_name}: {result.error}")

        # 2 + 3. Cascade: typed-match primero, safety-net después
        for fallback in self._ordered_fallbacks(prompt.intent):
            # RFC 2308: skip NXDOMAIN-cached providers
            if self._negative_cache.is_suppressed(
                fallback.provider_name, intent_key
            ):
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
                self._positive_cache.record_success(
                    fallback.provider_name, intent_key, latency_ms
                )
                tier = self._classify_tier(fallback, prompt.intent)
                self._emit_cascade_event(
                    prompt.intent, fallback.provider_name, tier, attempts,
                )
                self._validate_and_penalize(
                    fallback.provider_name, result.value, prompt.intent
                )
                return result
            # Record failure → suppress for TTL, scoped by intent
            self._negative_cache.record_failure(
                fallback.provider_name, intent_key
            )
            errors.append(f"{fallback.provider_name}: {result.error}")

        # Singularidad Negativa: todos fallaron
        self._emit_cascade_event(
            prompt.intent, None, CascadeTier.NONE, attempts,
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
            self._provider_pool.record_success(
                provider.provider_name, latency_ms
            )
            return Ok(response)
        except Exception as e:  # deliberate boundary — LLM providers can raise any type
            latency_ms = (time.monotonic() - start) * 1000
            self._provider_pool.record_failure(
                provider.provider_name, latency_ms
            )
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

        If drift is confirmed (confidence ≥ threshold), the provider’s
        weight in the pool is penalized by recording a synthetic failure.
        This makes the provider less likely to be selected in future calls.

        The response is still returned to the caller — DNSSEC doesn’t
        reject, it adjusts trust for future routing.
        """
        signal = self._intent_validator.validate(
            response, intent, provider_name
        )
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
