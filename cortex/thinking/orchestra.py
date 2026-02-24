# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.0 — Thought Orchestra.

N modelos pensando en paralelo con fusión por consenso.
El cerebro distribuido de CORTEX.

Modos de pensamiento::

    DEEP_REASONING — Modelos top-tier para análisis profundo
    CODE           — Especializados en generación/análisis de código
    CREATIVE       — Para ideación, naming, y pensamiento lateral
    SPEED          — Ultra-rápidos para decisiones instantáneas
    CONSENSUS      — Todos los disponibles para máxima confianza

Uso::

    async with ThoughtOrchestra() as orchestra:
        thought = await orchestra.think("¿Cuál es la raíz del bug?")
        print(thought.content, thought.confidence)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from cortex.llm.provider import LLMProvider, _load_presets
from cortex.llm.router import CortexLLMRouter, CortexPrompt
from cortex.thinking.fusion import (
    FusedThought,
    FusionStrategy,
    ModelResponse,
    ThoughtFusion,
)
from cortex.thinking.orchestra_introspection import OrchestraIntrospectionMixin
from cortex.thinking.pool import ProviderPool, ThinkingRecord
from cortex.thinking.presets import (
    DEFAULT_ROUTING,
    MODE_SYSTEM_PROMPTS,
    OrchestraConfig,
    ThinkingMode,
)
from cortex.thinking.semantic_router import SemanticRouter

__all__ = ["ThoughtOrchestra"]

logger = logging.getLogger("cortex.thinking.orchestra")


# ─── Thought Orchestra ──────────────────────────────────────────────


class ThoughtOrchestra(OrchestraIntrospectionMixin):
    """N modelos pensando en paralelo con fusión por consenso.

    Crea instancias de LLMProvider via pool reutilizable.
    Ejecuta en paralelo con asyncio.gather, retry en fallos,
    y fusiona los resultados con ThoughtFusion.

    Soporta context manager::

        async with ThoughtOrchestra() as o:
            result = await o.think("pregunta")
    """

    def __init__(
        self,
        config: OrchestraConfig | None = None,
        routing: dict[str, list[tuple[str, str]]] | None = None,
    ):
        self.config = config or OrchestraConfig()
        self._routing = routing or DEFAULT_ROUTING
        self._pool = ProviderPool()
        self._fusion: ThoughtFusion | None = None
        self._judge: LLMProvider | None = None
        self._semantic_router = SemanticRouter()
        self._initialized = False
        self._history: list[ThinkingRecord] = []
        self._available_cache: list[str] | None = None

    # ── Lifecycle ────────────────────────────────────────────────

    async def __aenter__(self) -> ThoughtOrchestra:
        self._initialize()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    def _initialize(self) -> None:
        """Lazy initialization: detecta qué providers tienen API key."""
        if self._initialized:
            return

        self._initialized = True
        available = self._detect_available_providers()
        self._available_cache = available

        logger.info(
            "ThoughtOrchestra: %d providers disponibles: %s",
            len(available),
            available,
        )

        if len(available) < self.config.min_models:
            logger.warning(
                "ThoughtOrchestra necesita mínimo %d providers, hay %d.",
                self.config.min_models,
                len(available),
            )

        self._judge = self._find_judge(available)
        self._fusion = ThoughtFusion(judge_provider=self._judge)

    @staticmethod
    def _detect_available_providers() -> list[str]:
        """Detecta providers con API key configurada."""
        presets = _load_presets()
        return [
            name
            for name, preset in presets.items()
            if preset.get("env_key") and os.environ.get(preset["env_key"])
        ]

    def _find_judge(self, available: list[str]) -> LLMProvider | None:
        """Encuentra el mejor provider disponible para actuar como juez."""
        judge_name = self.config.judge_provider
        if judge_name and judge_name in available:
            try:
                return self._pool.get(judge_name, self.config.judge_model or "")
            except (OSError, ValueError, KeyError) as e:
                logger.warning("Juez %s no disponible: %s", judge_name, e)

        presets = _load_presets()
        for fallback in ["openai", "anthropic", "gemini", "qwen", "deepseek"]:
            if fallback in available:
                try:
                    return self._pool.get(fallback, presets[fallback]["default_model"])
                except (OSError, ValueError, KeyError):
                    continue
        return None

    # ── Model Resolution ─────────────────────────────────────────

    def _resolve_models(self, mode: ThinkingMode | str) -> list[tuple[str, str]]:
        """Resuelve qué modelos usar para un modo dado."""
        mode_key = ThinkingMode(mode) if isinstance(mode, str) else mode
        candidates = self._routing.get(mode_key, [])

        presets = _load_presets()
        resolved = []
        for provider_name, model in candidates:
            preset = presets.get(provider_name)
            if not preset:
                continue
            env_key = preset.get("env_key", "")
            if env_key and os.environ.get(env_key):
                resolved.append((provider_name, model))
            if len(resolved) >= self.config.max_models:
                break

        return resolved

    # ── Query with Retry ──────────────────────────────────────────

    def _resolve_fallbacks(self, primary_provider_name: str) -> list[Any]:
        """Resuelve la lista de fallbacks excluyendo al primario."""
        fallbacks = []
        available = self._available_cache or self._detect_available_providers()
        for fb_name in ["openai", "anthropic", "gemini", "qwen", "deepseek"]:
            if fb_name in available and fb_name != primary_provider_name:
                try:
                    presets = _load_presets()
                    fb_model = presets[fb_name]["default_model"]
                    fallbacks.append(self._pool.get(fb_name, fb_model))
                except (OSError, ValueError, KeyError):
                    continue
        return fallbacks

    async def _execute_single_attempt(
        self,
        provider_name: str,
        model: str,
        prompt: str,
        system: str,
        attempt: int,
        attempts: int,
    ) -> tuple[ModelResponse | None, str | None]:
        """Ejecuta un único intento de consulta, manejando fallos y timeouts."""
        try:
            provider = self._pool.get(provider_name, model)
            fallbacks = self._resolve_fallbacks(provider_name)

            router = CortexLLMRouter(primary=provider, fallbacks=fallbacks)
            cortex_prompt = CortexPrompt(
                system_instruction=system,
                working_memory=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            result = await asyncio.wait_for(
                router.execute_resilient(cortex_prompt),
                timeout=self.config.timeout_seconds,
            )

            if result.is_ok():
                return ModelResponse(
                    provider=provider_name,
                    model=model,
                    content=result.unwrap(),
                    latency_ms=0.0,  # calculated in caller
                    token_count=len(result.unwrap().split()),
                ), None

            last_error = result.error
            logger.warning(
                "%s:%s ROP cascade failed (intento %d/%d): %s",
                provider_name,
                model,
                attempt + 1,
                attempts,
                last_error,
            )
            return None, last_error

        except asyncio.TimeoutError:
            last_error = f"Timeout ({self.config.timeout_seconds}s)"
            logger.warning(
                "%s:%s timeout (intento %d/%d)",
                provider_name,
                model,
                attempt + 1,
                attempts,
            )
            return None, last_error
        except (OSError, ValueError, KeyError) as e:
            last_error = str(e)
            logger.warning(
                "%s:%s error (intento %d/%d): %s",
                provider_name,
                model,
                attempt + 1,
                attempts,
                e,
            )
            return None, last_error

    async def _query_model(
        self,
        provider_name: str,
        model: str,
        prompt: str,
        system: str,
    ) -> ModelResponse:
        """Consulta un modelo individual con timeout y retry."""
        start = time.monotonic()
        last_error: str | None = None
        attempts = 2 if self.config.retry_on_failure else 1

        for attempt in range(attempts):
            response, last_error = await self._execute_single_attempt(
                provider_name, model, prompt, system, attempt, attempts
            )

            if response:
                response.latency_ms = (time.monotonic() - start) * 1000
                return response

            # Esperar antes de retry
            if attempt < attempts - 1:
                await asyncio.sleep(self.config.retry_delay_seconds)

        latency = (time.monotonic() - start) * 1000
        return ModelResponse(
            provider=provider_name,
            model=model,
            content="",
            latency_ms=latency,
            error=last_error,
        )

    # ── Main Think API ────────────────────────────────────────────

    async def think(
        self,
        prompt: str,
        mode: str = "deep_reasoning",
        system: str | None = None,
        strategy: FusionStrategy | str | None = None,
    ) -> FusedThought:
        """Pensamiento multi-modelo con fusión.

        Args:
            prompt: La pregunta o tarea.
            mode: Modo de pensamiento.
            system: System prompt (None = usa el específico del modo).
            strategy: Estrategia de fusión (None = default del config).

        Returns:
            FusedThought con respuesta fusionada, confidence, y metadatos.
        """
        self._initialize()

        # Auto-routing: classify prompt semantically
        if mode == "auto":
            route = self._semantic_router.classify(prompt)
            mode = route.mode.value
            logger.info(
                "🧭 SemanticRouter: auto → %s (confidence=%.2f, %s)",
                mode,
                route.confidence,
                route.reason,
            )

        models = self._resolve_models(mode)

        if not models:
            logger.error("No hay modelos para modo '%s'.", mode)
            return FusedThought(
                content="Error: no hay modelos disponibles. Configura API keys.",
                strategy=FusionStrategy.MAJORITY,
                confidence=0.0,
            )

        # Resolver system prompt
        if system is None and self.config.use_mode_prompts:
            system = MODE_SYSTEM_PROMPTS.get(mode, MODE_SYSTEM_PROMPTS[ThinkingMode.DEEP_REASONING])
        elif system is None:
            system = "You are a world-class reasoning AI. Think step by step."

        # Resolver estrategia
        if strategy is None:
            fusion_strategy = self.config.default_strategy
        elif isinstance(strategy, str):
            fusion_strategy = FusionStrategy(strategy)
        else:
            fusion_strategy = strategy

        logger.info(
            "🎭 Think [%s] × %d modelos | strategy=%s",
            mode,
            len(models),
            fusion_strategy.value,
        )

        # Ejecución paralela
        start = time.monotonic()
        responses = await asyncio.gather(
            *[self._query_model(p, m, prompt, system) for p, m in models]
        )
        total_ms = (time.monotonic() - start) * 1000

        ok_count = sum(1 for r in responses if r.ok)
        logger.info(
            "🎭 Think completado: %.0fms | %d/%d exitosos",
            total_ms,
            ok_count,
            len(responses),
        )

        # Fusionar
        result = await self._fusion.fuse(
            responses=list(responses),
            original_prompt=prompt,
            strategy=fusion_strategy,
        )

        # Metadatos del orchestra
        result.meta.update(
            {
                "mode": mode,
                "total_latency_ms": round(total_ms, 1),
                "models_queried": len(models),
                "models_succeeded": ok_count,
                "pool_size": self._pool.size,
            }
        )

        # Registrar en historial
        self._history.append(
            ThinkingRecord(
                mode=mode,
                strategy=fusion_strategy.value,
                models_queried=len(models),
                models_succeeded=ok_count,
                total_latency_ms=total_ms,
                confidence=result.confidence,
                agreement=result.agreement_score,
                winner=result.meta.get("winner"),
            )
        )

        return result

    # ── Cleanup ───────────────────────────────────────────────────

    async def close(self) -> None:
        """Cerrar todas las conexiones del pool."""
        await self._pool.close_all()

    # Convenience and introspection methods provided by OrchestraIntrospectionMixin:
    #   quick_think, deep_think, code_think, creative_think, consensus_think,
    #   available_modes (property), history (property), status(), stats()
