# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.2 — Sovereign LLM Routing (KETER-∞ ROP).

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
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Sequence
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

    def __init__(
        self,
        primary: BaseProvider,
        fallbacks: Sequence[BaseProvider] | None = None,
        *,
        negative_ttl: float = 300.0,
    ) -> None:
        self._primary = primary
        self._fallbacks = list(fallbacks) if fallbacks else []
        self._negative_cache: dict[str, float] = {}
        self._negative_ttl = negative_ttl

    @property
    def primary(self) -> BaseProvider:
        return self._primary

    @property
    def fallbacks(self) -> list[BaseProvider]:
        return self._fallbacks

    # ── Negative Cache (NXDOMAIN Pattern) ─────────────────────────────────

    def _is_cached_failure(self, provider: BaseProvider) -> bool:
        """Check if a provider has a non-expired negative-cache entry."""
        ts = self._negative_cache.get(provider.provider_name)
        if ts is None:
            return False
        if (time.monotonic() - ts) > self._negative_ttl:
            del self._negative_cache[provider.provider_name]
            return False  # TTL expired → retry
        return True  # still hot → skip

    def _record_failure(self, provider: BaseProvider) -> None:
        """Record a provider failure timestamp for negative caching."""
        self._negative_cache[provider.provider_name] = time.monotonic()

    def clear_negative_cache(self) -> None:
        """Flush the negative cache — forces retry of all providers."""
        self._negative_cache.clear()

    # ── Internal ──────────────────────────────────────────────────────────

    def _ordered_fallbacks(self, intent: IntentProfile) -> list[BaseProvider]:
        """Ordena los fallbacks por afinidad de intención.

        Semántica:
        - El prompt usa GENERAL → sin filtro, cascade completo en orden de registro.
        - El prompt usa intent específico (CODE, REASONING, CREATIVE):
            * typed-match  → provider con el intent específico en su afinidad.
            * safety-net   → providers GENERAL o sin afinidad específica (van al final).

        Invariante: el safety-net nunca se elimina, solo se retrasa.
        """
        if intent is IntentProfile.GENERAL:
            return list(self._fallbacks)

        typed: list[BaseProvider] = []
        untyped: list[BaseProvider] = []

        for fb in self._fallbacks:
            affinity = fb.intent_affinity
            # typed-match: el provider declara explícitamente este intent
            if intent in affinity:
                typed.append(fb)
            else:
                # safety-net: provider GENERAL u otros dominios
                untyped.append(fb)

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

    async def execute_resilient(self, prompt: CortexPrompt) -> Result[str, str]:
        """Ejecuta inferencia con cascade determinista por intención.

        Ok(response) en éxito, Err(detail) si todos los proveedores fallan.
        Providers con negative-cache activo se saltan (NXDOMAIN pattern).
        """
        errors: list[str] = []

        # 1. Primario — sin filtro de intención (respeta negative cache)
        if self._is_cached_failure(self._primary):
            errors.append(f"{self._primary.provider_name}: negative-cached")
            logger.debug("Skipping '%s' — negative-cached", self._primary.provider_name)
        else:
            result = await self._try_provider(self._primary, prompt)
            if isinstance(result, Ok):
                return result
            errors.append(f"{self._primary.provider_name}: {result.error}")

        # 2 + 3. Cascade: typed-match primero, safety-net después
        for fallback in self._ordered_fallbacks(prompt.intent):
            if self._is_cached_failure(fallback):
                errors.append(f"{fallback.provider_name}: negative-cached")
                logger.debug("Skipping '%s' — negative-cached", fallback.provider_name)
                continue
            result = await self._try_provider(fallback, prompt)
            if isinstance(result, Ok):
                return result
            errors.append(f"{fallback.provider_name}: {result.error}")

        # Singularidad Negativa: todos fallaron
        detail = " | ".join(errors)
        logger.error("Singularidad Negativa [intent=%s]: %s", prompt.intent.value, detail)
        return Err(f"All providers failed: {detail}")

    async def _try_provider(self, provider: BaseProvider, prompt: CortexPrompt) -> Result[str, str]:
        """Try a single provider, returning Result. Records failure for negative caching."""
        try:
            response = await provider.invoke(prompt)
            return Ok(response)
        except Exception as e:  # deliberate boundary — LLM providers can raise any type
            self._record_failure(provider)
            logger.warning(
                "Provider '%s' failed [intent=%s]: %s (negative-cached for %.0fs)",
                provider.provider_name,
                prompt.intent.value,
                e,
                self._negative_ttl,
            )
            return Err(str(e))

    async def invoke(self, prompt: CortexPrompt) -> Result[str, str]:
        """Primary entry point — alias for execute_resilient."""
        return await self.execute_resilient(prompt)
