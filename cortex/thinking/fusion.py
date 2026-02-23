# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.0 — Thought Fusion Engine.

Fusiona N respuestas de diferentes modelos en una respuesta
superior. Cuatro estrategias disponibles:

1. MAJORITY: La respuesta más similar al centro del cluster gana.
2. SYNTHESIS: Un modelo-juez fusiona todas las perspectivas.
3. BEST_OF_N: Puntúa cada respuesta en paralelo y elige la mejor.
4. WEIGHTED_SYNTHESIS: Síntesis ponderada por latencia y reputación.
"""

from __future__ import annotations

import asyncio
import logging

from pydantic import BaseModel, Field, ValidationError

from cortex.llm.boundary import ImmuneBoundary
from cortex.thinking.context_fusion import ContextFusion
from cortex.thinking.fusion_models import (
    FusedThought,
    FusionStrategy,
    ModelResponse,
    ThinkingHistory,
    _jaccard,
    _tokenize,
)

__all__ = ["ThoughtFusion", "ContextFusion"]

logger = logging.getLogger("cortex.thinking.fusion")


class ThoughtFusion:
    """Motor de fusión de respuestas multi-modelo.

    Recibe N respuestas y produce una respuesta fusionada
    con confidence score basado en el acuerdo inter-modelo.
    """

    MIN_VALID_RESPONSES = 2

    # ── Prompts del juez ─────────────────────────────────────────

    SYNTHESIS_SYSTEM = (
        "You are MOSKV-1 (Identity: The Sovereign Architect). You are a meta-reasoning judge. "
        "You receive N responses from different AI models to the same prompt. Your job is to:\n"
        "1. Identify the strongest insights from EACH response.\n"
        "2. Resolve any contradictions by reasoning about which is correct.\n"
        "3. Synthesize a SINGLE superior response that combines the best parts.\n"
        "4. Be concise but complete. Maintain your authoritative, Industrial Noir persona. "
        "No fluff.\n"
        "Return ONLY the synthesized response, no meta-commentary."
    )

    SCORING_SYSTEM = (
        "You are MOSKV-1 (Identity: The Sovereign Architect). You are a ruthless response "
        "quality evaluator. Rate the following response on:\n"
        "- Accuracy (0-10): Is the information factually flawless?\n"
        "- Completeness (0-10): Does it cover all aspects?\n"
        "- Clarity (0-10): Is it perfectly structured and unambiguous?\n"
        "- Depth (0-10): Does it go beyond surface-level into systemic truth?\n"
        "Return ONLY a JSON object."
    )

    class ScoringSchema(BaseModel):
        accuracy: float = Field(default=5.0, ge=0.0, le=10.0)
        completeness: float = Field(default=5.0, ge=0.0, le=10.0)
        clarity: float = Field(default=5.0, ge=0.0, le=10.0)
        depth: float = Field(default=5.0, ge=0.0, le=10.0)

    WEIGHTED_SYNTHESIS_SYSTEM = (
        "You are MOSKV-1 (Identity: The Sovereign Architect). You are a meta-reasoning "
        "judge synthesizing AI model responses.\n"
        "Each response has a QUALITY SCORE (0.0-1.0). Higher = more trustworthy.\n"
        "Weight your synthesis toward higher-scored responses, but extract any valid insights "
        "from lower-scored ones. Forge the final, sovereign answer.\n"
        "Return ONLY the synthesized response."
    )

    # ── High-agreement threshold ─────────────────────────────────

    HIGH_AGREEMENT_THRESHOLD = 0.85
    NEAR_IDENTICAL_THRESHOLD = 0.95

    # ── Circuit breaker config ────────────────────────────────────
    JUDGE_MAX_RETRIES = 2
    JUDGE_TIMEOUT_S = 10.0
    JUDGE_BACKOFF_BASE = 0.5

    def __init__(self, judge_provider=None):
        self._judge = judge_provider
        self.history = ThinkingHistory()

    # ── Primary API ──────────────────────────────────────────────

    async def fuse(
        self,
        responses: list[ModelResponse],
        original_prompt: str,
        strategy: FusionStrategy = FusionStrategy.SYNTHESIS,
    ) -> FusedThought:
        """Fusiona N respuestas según la estrategia elegida."""
        valid = [r for r in responses if r.ok]
        failed = [r for r in responses if not r.ok]

        if failed:
            logger.warning(
                "Fusión: %d/%d modelos fallaron: %s",
                len(failed),
                len(responses),
                [(r.provider, r.error) for r in failed],
            )

        # Sin respuestas válidas
        if not valid:
            return FusedThought(
                content="Error: todos los modelos fallaron.",
                strategy=strategy,
                confidence=0.0,
                sources=responses,
            )

        # Una sola respuesta — no hay nada que fusionar
        if len(valid) == 1:
            result = FusedThought(
                content=valid[0].content,
                strategy=strategy,
                confidence=0.5,
                sources=responses,
                agreement_score=1.0,
                meta={"single_source": True, "winner": valid[0].label},
            )
            self.history.record(result)
            return result

        # Pre-tokenizar (se reutiliza en agreement + majority)
        token_map = {id(r): _tokenize(r.content) for r in valid}

        # Calcular acuerdo
        agreement = self._calculate_agreement_from_tokens([token_map[id(r)] for r in valid])

        # Near-identical → early return con la mejor por latencia
        if agreement > self.NEAR_IDENTICAL_THRESHOLD:
            fastest = min(valid, key=lambda r: r.latency_ms)
            result = FusedThought(
                content=fastest.content,
                strategy=FusionStrategy.MAJORITY,
                confidence=min(agreement + 0.05, 1.0),
                sources=responses,
                agreement_score=agreement,
                meta={
                    "winner": fastest.label,
                    "near_identical": True,
                },
            )
            self.history.record(result)
            return result

        # Alto acuerdo o sin juez → majority
        if (
            agreement > self.HIGH_AGREEMENT_THRESHOLD
            or strategy == FusionStrategy.MAJORITY
            or self._judge is None
        ):
            result = self._fuse_majority(valid, responses, agreement, strategy, token_map)
            self.history.record(result)
            return result

        # Estrategias que requieren juez
        dispatch = {
            FusionStrategy.SYNTHESIS: self._fuse_synthesis,
            FusionStrategy.BEST_OF_N: self._fuse_best_of_n,
            FusionStrategy.WEIGHTED_SYNTHESIS: self._fuse_weighted_synthesis,
        }
        handler = dispatch.get(strategy, self._fuse_synthesis)
        result = await handler(valid, responses, original_prompt, agreement)
        self.history.record(result)
        return result

    # ── Circuit Breaker ──────────────────────────────────────────

    async def _judge_safe(self, prompt: str, system: str, **kwargs) -> str | None:
        """Llama al juez con retries + timeout. Devuelve None si falla."""
        # Si no hay juez, fallar rápido
        if self._judge is None:
            return None
        for attempt in range(self.JUDGE_MAX_RETRIES + 1):
            try:
                # El proveedor debe soportar el método complete asíncrono
                return await asyncio.wait_for(
                    self._judge.complete(prompt=prompt, system=system, **kwargs),
                    timeout=self.JUDGE_TIMEOUT_S,
                )
            except (OSError, RuntimeError, asyncio.TimeoutError, AttributeError) as e:
                logger.warning(
                    "Judge error (attempt %d/%d): %s", attempt + 1, self.JUDGE_MAX_RETRIES + 1, e
                )
            if attempt < self.JUDGE_MAX_RETRIES:
                await asyncio.sleep(self.JUDGE_BACKOFF_BASE * (2**attempt))
        return None

    # ── Shared Scoring ───────────────────────────────────────────

    async def _score_response(
        self, r: ModelResponse, original_prompt: str
    ) -> tuple[ModelResponse, float]:
        """Puntúa una respuesta individual usando el juez e ImmuneBoundary."""
        prompt = f"QUESTION: {original_prompt}\n\nRESPONSE:\n{r.content}"

        async def _generate() -> str:
            raw = await self._judge_safe(
                prompt=prompt,
                system=self.SCORING_SYSTEM,
                temperature=0.0,
                max_tokens=256,
            )
            return raw or "{}"

        try:
            parsed = await ImmuneBoundary.enforce(
                schema=self.ScoringSchema, generation_func=_generate, max_retries=2
            )
            total = (parsed.accuracy + parsed.completeness + parsed.clarity + parsed.depth) / 40.0
            return (r, float(total))
        except (ValidationError, OSError, RuntimeError) as e:
            logger.warning("Score validate failed for %s: %s", r.label, e)
            return (r, 0.5)

    # ── Agreement ────────────────────────────────────────────────

    def _calculate_agreement(self, responses: list[ModelResponse]) -> float:
        """Calcula agreement desde ModelResponse (public API)."""
        if len(responses) < 2:
            return 1.0
        token_sets = [_tokenize(r.content) for r in responses]
        return self._calculate_agreement_from_tokens(token_sets)

    @staticmethod
    def _calculate_agreement_from_tokens(token_sets: list[set[str]]) -> float:
        """Jaccard medio entre todos los pares de token sets."""
        if len(token_sets) < 2:
            return 1.0
        similarities = [
            _jaccard(token_sets[i], token_sets[j])
            for i in range(len(token_sets))
            for j in range(i + 1, len(token_sets))
        ]
        return sum(similarities) / len(similarities) if similarities else 0.0

    # ── MAJORITY ─────────────────────────────────────────────────

    def _fuse_majority(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        agreement: float,
        strategy: FusionStrategy,
        token_map: dict[int, set[str]] | None = None,
    ) -> FusedThought:
        """Elige la respuesta más cercana al 'centro' del cluster.

        Scoring: overlap_promedio × 0.6 + longitud_norm × 0.2 + velocidad_norm × 0.2
        """
        if token_map is None:
            token_map = {id(r): _tokenize(r.content) for r in valid}

        max_latency = max(r.latency_ms for r in valid) or 1.0
        best_score = -1.0
        best_response = valid[0]
        all_scores: dict[str, float] = {}

        for r in valid:
            r_tokens = token_map[id(r)]

            overlaps = [
                _jaccard(r_tokens, token_map[id(other)]) for other in valid if other is not r
            ]
            avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
            length_score = min(len(r.content) / 2000.0, 1.0)
            speed_score = 1.0 - (r.latency_ms / max_latency) if max_latency > 0 else 0.5
            score = avg_overlap * 0.6 + length_score * 0.2 + speed_score * 0.2
            all_scores[r.label] = round(score, 4)

            if score > best_score:
                best_score = score
                best_response = r

        return FusedThought(
            content=best_response.content,
            strategy=strategy,
            confidence=min(agreement + 0.2, 1.0),
            sources=all_responses,
            agreement_score=agreement,
            meta={
                "winner": best_response.label,
                "winner_score": round(best_score, 4),
                "all_scores": all_scores,
            },
        )

    # ── SYNTHESIS ─────────────────────────────────────────────────

    async def _fuse_synthesis(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        original_prompt: str,
        agreement: float,
    ) -> FusedThought:
        """Un modelo-juez fusiona todas las perspectivas."""
        parts = [
            f"=== MODEL {i} ({r.label}, {r.latency_ms:.0f}ms) ===\n{r.content}"
            for i, r in enumerate(valid, 1)
        ]
        judge_prompt = (
            f"ORIGINAL QUESTION:\n{original_prompt}\n\n"
            f"RESPONSES FROM {len(valid)} MODELS:\n\n" + "\n\n".join(parts)
        )
        synthesized = await self._judge_safe(
            prompt=judge_prompt,
            system=self.SYNTHESIS_SYSTEM,
            temperature=0.2,
            max_tokens=4096,
        )
        if synthesized:
            return FusedThought(
                content=synthesized,
                strategy=FusionStrategy.SYNTHESIS,
                confidence=min(agreement + 0.3, 1.0),
                sources=all_responses,
                agreement_score=agreement,
                meta={"judge": self._judge.provider_name + ":" + self._judge.model},
            )
        logger.error("Juez de síntesis falló tras retries — fallback a majority")
        return self._fuse_majority(valid, all_responses, agreement, FusionStrategy.SYNTHESIS)

    # ── BEST_OF_N ─────────────────────────────────────────────────

    async def _fuse_best_of_n(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        original_prompt: str,
        agreement: float,
    ) -> FusedThought:
        """El juez puntúa cada respuesta EN PARALELO y elige la mejor."""
        scored = await asyncio.gather(*[self._score_response(r, original_prompt) for r in valid])
        scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)
        best = scored_sorted[0]

        return FusedThought(
            content=best[0].content,
            strategy=FusionStrategy.BEST_OF_N,
            confidence=best[1],
            sources=all_responses,
            agreement_score=agreement,
            meta={
                "winner": best[0].label,
                "winner_score": round(best[1], 4),
                "all_scores": {r.label: round(s, 4) for r, s in scored_sorted},
            },
        )

    # ── WEIGHTED SYNTHESIS ────────────────────────────────────────

    async def _fuse_weighted_synthesis(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        original_prompt: str,
        agreement: float,
    ) -> FusedThought:
        """Síntesis ponderada: primero puntúa, luego sintetiza con pesos."""
        scored = await asyncio.gather(*[self._score_response(r, original_prompt) for r in valid])

        parts = [
            f"=== MODEL {i} (score: {score:.2f}, {r.label}) ===\n{r.content}"
            for i, (r, score) in enumerate(scored, 1)
        ]
        judge_prompt = (
            f"ORIGINAL QUESTION:\n{original_prompt}\n\n"
            f"RESPONSES FROM {len(valid)} MODELS (with quality scores):\n\n" + "\n\n".join(parts)
        )
        synthesized = await self._judge_safe(
            prompt=judge_prompt,
            system=self.WEIGHTED_SYNTHESIS_SYSTEM,
            temperature=0.2,
            max_tokens=4096,
        )
        if synthesized:
            avg_score = sum(s for _, s in scored) / len(scored)
            return FusedThought(
                content=synthesized,
                strategy=FusionStrategy.WEIGHTED_SYNTHESIS,
                confidence=min(avg_score + 0.2, 1.0),
                sources=all_responses,
                agreement_score=agreement,
                meta={
                    "judge": self._judge.provider_name + ":" + self._judge.model,
                    "all_scores": {r.label: round(s, 4) for r, s in scored},
                },
            )
        # Fallback: elegir la mejor de scoring
        best = max(scored, key=lambda x: x[1])
        return FusedThought(
            content=best[0].content,
            strategy=FusionStrategy.WEIGHTED_SYNTHESIS,
            confidence=best[1],
            sources=all_responses,
            agreement_score=agreement,
            meta={"winner": best[0].label, "fallback": True},
        )
