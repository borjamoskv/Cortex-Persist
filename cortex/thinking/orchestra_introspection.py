# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.1 — Thought Orchestra: Introspection Mixin.

Extracted from orchestra.py to keep file size under 400 LOC.
Contains status, stats, history, and convenience think methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.thinking.fusion import FusedThought

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
        return await self.think(prompt, mode="quick")

    async def deep_think(self, prompt: str) -> FusedThought:
        """Razonamiento profundo con síntesis."""
        return await self.think(prompt, mode="deep_reasoning", strategy="synthesis")

    async def code_think(self, prompt: str) -> FusedThought:
        """Análisis de código con best-of-n."""
        return await self.think(prompt, mode="code_analysis", strategy="best_of_n")

    async def creative_think(self, prompt: str) -> FusedThought:
        """Pensamiento creativo con weighted synthesis."""
        return await self.think(prompt, mode="creative", strategy="weighted")

    async def consensus_think(self, prompt: str) -> FusedThought:
        """Máximo consenso — todos los modelos con síntesis."""
        return await self.think(prompt, mode="consensus", strategy="synthesis")

    # ── Introspection Properties ──────────────────────────────────

    @property
    def available_modes(self) -> list[str]:
        """Modos con al menos 1 modelo configurado."""
        from cortex.thinking.presets import ThinkingMode

        return [m.value for m in ThinkingMode if self._resolve_models(m)]

    @property
    def history(self) -> list:
        """Historial de pensamientos (más reciente al final)."""
        return self._history

    def status(self) -> dict[str, Any]:
        """Estado completo del orchestra."""
        from cortex.thinking.presets import ThinkingMode

        mode_status = {}
        for mode in ThinkingMode:
            models = self._resolve_models(mode)
            mode_status[mode.value] = {
                "models": [f"{p}:{m}" for p, m in models],
                "count": len(models),
                "ready": len(models) >= self.config.min_models,
            }

        return {
            "initialized": self._initialized,
            "judge": (f"{self._judge.provider_name}:{self._judge.model}" if self._judge else None),
            "pool_size": self._pool.size,
            "history_count": len(self._history),
            "modes": mode_status,
            "config": {
                "min_models": self.config.min_models,
                "max_models": self.config.max_models,
                "timeout_seconds": self.config.timeout_seconds,
                "default_strategy": self.config.default_strategy.value,
                "retry_on_failure": self.config.retry_on_failure,
                "use_mode_prompts": self.config.use_mode_prompts,
            },
        }

    def stats(self) -> dict[str, Any]:
        """Estadísticas agregadas del historial."""
        if not self._history:
            return {"total_thoughts": 0}

        total = len(self._history)
        avg_confidence = sum(r.confidence for r in self._history) / total
        avg_agreement = sum(r.agreement for r in self._history) / total
        avg_latency = sum(r.total_latency_ms for r in self._history) / total
        success_rate = (
            sum(
                r.models_succeeded / r.models_queried for r in self._history if r.models_queried > 0
            )
            / total
        )

        # Proveedor que más gana
        winner_counts: dict[str, int] = {}
        for r in self._history:
            if r.winner:
                provider = r.winner.split(":")[0]
                winner_counts[provider] = winner_counts.get(provider, 0) + 1
        top_winner = max(winner_counts, key=winner_counts.get) if winner_counts else None

        return {
            "total_thoughts": total,
            "avg_confidence": round(avg_confidence, 3),
            "avg_agreement": round(avg_agreement, 3),
            "avg_latency_ms": round(avg_latency, 1),
            "model_success_rate": round(success_rate, 3),
            "top_winning_provider": top_winner,
            "mode_distribution": {
                mode: sum(1 for r in self._history if r.mode == mode)
                for mode in {r.mode for r in self._history}
            },
        }
