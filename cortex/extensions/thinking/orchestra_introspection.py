# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.1 — Thought Orchestra: Introspection Mixin.

Extracted from orchestra.py to keep file size under 400 LOC.
Contains status, stats, history, and convenience think methods.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger("cortex.extensions.thinking")

if TYPE_CHECKING:
    from cortex.extensions.thinking.fusion import FusedThought

__all__ = ["OrchestraIntrospectionMixin"]


class OrchestraIntrospectionMixin:
    """Mixin providing introspection and convenience methods for ThoughtOrchestra.

    Requires the host class to have:
        - self._initialized: bool
        - self._history: list[ThinkingRecord]
        - self._judge: LLMProvider | None
        - self._pool: ProviderPool
        - self.config: OrchestraConfig
        - self._resolve_models(mode) -> list[tuple[str, str]]
        - self.think(prompt, mode, strategy) -> FusedThought
    """

    # ── Convenience Think Methods ─────────────────────────────────

    async def quick_think(self, prompt: str) -> FusedThought:
        """Pensamiento rápido. Retorna solo el contenido."""
        return await self.think(prompt, mode="quick")  # type: ignore[reportAttributeAccessIssue]

    async def deep_think(self, prompt: str) -> FusedThought:
        """Razonamiento profundo con síntesis."""
        return await self.think( # type: ignore[reportAttributeAccessIssue]
            prompt, mode="deep_reasoning", strategy="synthesis"  
        )

    async def code_think(self, prompt: str) -> FusedThought:
        """Análisis de código con best-of-n."""
        return await self.think( # type: ignore[reportAttributeAccessIssue]
            prompt, mode="code_analysis", strategy="best_of_n"  
        )

    async def creative_think(self, prompt: str) -> FusedThought:
        """Pensamiento creativo con weighted synthesis."""
        return await self.think( # type: ignore[reportAttributeAccessIssue]
            prompt, mode="creative", strategy="weighted"  
        )

    async def consensus_think(self, prompt: str) -> FusedThought:
        """Máximo consenso — todos los modelos con síntesis."""
        return await self.think( # type: ignore[reportAttributeAccessIssue]
            prompt, mode="consensus", strategy="synthesis"  
        )

    async def omega_think(self, prompt: str) -> FusedThought:
        """Omega Reasoning Protocol (ORP) — Adversarial Truth Collapse.

        1. Generates consensus hypothesis (ThinkingMode.OMEGA).
        2. Subjects the hypothesis to an Inquisitorial siege (Red Team).
        3. Folds the siege critique into a final, invulnerable response.
        """
        from cortex.extensions.llm.sovereign import Inquisitor

        # Phase 1: Hypothesis Synthesis
        hypothesis = await self.think( # type: ignore[reportAttributeAccessIssue]
            prompt, mode="omega", strategy="synthesis"  
        )

        # Phase 2: Inquisitorial Siege (Asymmetry Ω₅)
        inquisitor = Inquisitor()
        siege = await inquisitor.asediar(hypothesis.content, original_prompt=prompt)

        # Phase 3: Truth Folding (with Multi-round Refinement Ω₅)
        # Extend ORP to multi-round adversarial refinement if confidence < 0.8 after first siege.
        # (Ghost 3181 resolution)
        refinement_prompt = (
            f"ORIGINAL INTENT: {prompt}\n\n"
            f"PROPOSED HYPOTHESIS: {hypothesis.content}\n\n"
            f"INQUISITORIAL CRITIQUE: {siege.content}\n\n"
            f"MISSION: Forge a final response that resolves ALL critiques and satisfies "
            f"the original intent with zero-defect architecture."
        )

        final_thought = await self.think(  # type: ignore[reportAttributeAccessIssue]
            refinement_prompt, mode="deep_reasoning", strategy="synthesis"
        )

        # Logic for Multi-round Refinement (Ω₅)
        if final_thought.confidence < 0.8:
            logger.info(
                "🛡️ [ORP] Low confidence (%.2f). Starting second round of adversarial refinement.",
                final_thought.confidence,
            )
            siege_2 = await inquisitor.asediar(final_thought.content, original_prompt=prompt)
            refinement_prompt_2 = (
                f"ORIGINAL INTENT: {prompt}\n\n"
                f"PREVIOUS BEST: {final_thought.content}\n\n"
                f"SECOND CRITIQUE: {siege_2.content}\n\n"
                f"MISSION: Absolute perfection. Resolve remaining blind spots."
            )
            final_thought = await self.think(  # type: ignore[reportAttributeAccessIssue]
                refinement_prompt_2, mode="deep_reasoning", strategy="synthesis"
            )

        # Merge metadata
        final_thought.meta.update(
            {
                "orp_active": True,
                "siege_result": siege.content[:500] + "...",
                "initial_hypothesis_confidence": hypothesis.confidence,
                "orp_multi_round": final_thought.confidence
                < 0.8,  # Track if multi-round was triggered
            }
        )
        return final_thought

    # ── Introspection Properties ──────────────────────────────────

    @property
    def available_modes(self) -> list[str]:
        """Modos con al menos 1 modelo configurado."""
        from cortex.extensions.thinking.presets import ThinkingMode

        return [m.value for m in ThinkingMode if self._resolve_models(m)]  # type: ignore[reportAttributeAccessIssue]

    @property
    def history(self) -> list:
        """Historial de pensamientos (más reciente al final)."""
        return self._history  # type: ignore[reportAttributeAccessIssue]

    def status(self) -> dict[str, Any]:
        """Estado completo del orchestra."""
        from cortex.extensions.thinking.presets import ThinkingMode

        mode_status = {}
        for mode in ThinkingMode:
            models = self._resolve_models(mode)  # type: ignore[reportAttributeAccessIssue]
            mode_status[mode.value] = {
                "models": [f"{p}:{m}" for p, m in models],
                "count": len(models),
                "ready": len(models) >= self.config.min_models,  # type: ignore[reportAttributeAccessIssue]
            }

        return {
            "initialized": self._initialized,  # type: ignore[reportAttributeAccessIssue]
            "judge": (
                f"{self._judge.provider_name}:{self._judge.model}"  # type: ignore[type-error]
                if self._judge else None  # type: ignore[type-error]
            ),  # type: ignore[reportAttributeAccessIssue]
            "pool_size": self._pool.size,  # type: ignore[reportAttributeAccessIssue]
            "history_count": len(self._history),  # type: ignore[reportAttributeAccessIssue]
            "modes": mode_status,
            "config": {
                "min_models": self.config.min_models,  # type: ignore[reportAttributeAccessIssue]
                "max_models": self.config.max_models,  # type: ignore[reportAttributeAccessIssue]
                "timeout_seconds": self.config.timeout_seconds,  # type: ignore[reportAttributeAccessIssue]
                "default_strategy": self.config.default_strategy.value,  # type: ignore[reportAttributeAccessIssue]
                "retry_on_failure": self.config.retry_on_failure,  # type: ignore[reportAttributeAccessIssue]
                "use_mode_prompts": self.config.use_mode_prompts,  # type: ignore[reportAttributeAccessIssue]
            },
        }

    def stats(self) -> dict[str, Any]:
        """Estadísticas agregadas del historial."""
        if not self._history:  # type: ignore[reportAttributeAccessIssue]
            return {"total_thoughts": 0}

        total = len(self._history)  # type: ignore[reportAttributeAccessIssue]
        avg_confidence = float(sum(r.confidence for r in self._history) / total)  # type: ignore[reportAttributeAccessIssue]
        avg_agreement = float(sum(r.agreement for r in self._history) / total)  # type: ignore[reportAttributeAccessIssue]
        avg_latency = float(sum(r.total_latency_ms for r in self._history) / total)  # type: ignore[reportAttributeAccessIssue]
        success_rate = float(
            sum(
                r.models_succeeded / r.models_queried
                for r in self._history  # type: ignore[reportAttributeAccessIssue]
                if r.models_queried > 0 
            )
            / total
        )

        # Proveedor que más gana
        winner_counts: dict[str, int] = {}
        for r in self._history:  # type: ignore[reportAttributeAccessIssue]
            if r.winner:
                provider = r.winner.split(":")[0]
                winner_counts[provider] = winner_counts.get(provider, 0) + 1
        top_winner = max(winner_counts, key=winner_counts.get) if winner_counts else None  # type: ignore[reportCallIssue,reportArgumentType]

        return {
            "total_thoughts": total,
            "avg_confidence": round(avg_confidence, 3),
            "avg_agreement": round(avg_agreement, 3),
            "avg_latency_ms": round(avg_latency, 1),
            "model_success_rate": round(success_rate, 3),
            "top_winning_provider": top_winner,
            "mode_distribution": {
                mode: sum(1 for r in self._history if r.mode == mode)  # type: ignore[reportAttributeAccessIssue]
                for mode in {r.mode for r in self._history}  # type: ignore[reportAttributeAccessIssue]
            },
        }
