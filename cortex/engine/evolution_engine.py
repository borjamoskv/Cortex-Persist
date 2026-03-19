"""
CORTEX Phase 2 (v3) - Continuous Improvement Engine
Bio-inspired Computational Evolution Architecture - Orchestrator
"""

from __future__ import annotations

import random
import time
from typing import Any

from cortex.engine.evolution_metrics import CortexMetrics
from cortex.engine.evolution_types import (
    DomainMetrics,
    ImprovementStrategy,
    SovereignAgent,
    SubAgent,
)
from cortex.engine.zero_prompting import ZeroPromptingEvolutionStrategy

# ==============================================================================
# EVOLUTIONARY STRATEGIES
# ==============================================================================


class ParameterTuningStrategy:
    """
    Eigen (1971) — Quasispecies Error Threshold.
    Adaptive mutation rates based on error_rate to avoid error catastrophe.
    """

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: CortexMetrics,
    ) -> dict[str, Any] | None:
        if metrics.health_score > 0.9:
            return None  # Sovereign-grade: no tuning needed

        scale = 0.5 + 2.5 * metrics.error_rate
        delta = scale * random.uniform(0.5, 1.2)

        for param in subagent.mutation.parameters:
            current = subagent.mutation.parameters[param]
            sign = 1 if random.random() > 0.5 else -1
            subagent.mutation.parameters[param] = current + sign * delta * 0.1 * abs(current)

        subagent.mutation.record_change(f"ParameterTuning (scale={scale:.2f}, δ={delta:.2f})")
        return {"strategy": "ParameterTuning", "scale": scale, "delta": delta}


class PruneDeadPathStrategy:
    """
    Fisher (1930) — Purifying Selection / Fundamental Theorem.
    Removes deleterious paths based on ghost_density (mutation load).
    """

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: CortexMetrics,
    ) -> dict[str, Any] | None:
        if subagent.generation <= 5:
            return None

        threshold = 20.0 + 20.0 * metrics.ghost_density
        if subagent.fitness >= threshold:
            return None

        subagent.is_active = False
        delta_fitness = 1.0 + metrics.ghost_density * 2.0
        return {
            "strategy": "PruneDeadPath",
            "pruned_agent": subagent.agent_id,
            "threshold": threshold,
            "delta_fitness": delta_fitness,
        }


class HeuristicInjectionStrategy:
    """
    Ochman (2000) — Horizontal Gene Transfer (HGT).
    Injects validated heuristics from domain knowledge into low-fitness agents.
    """

    DOMAIN_WEIGHTS: dict[str, float] = {
        "EVOLUTION": 1.0,
        "SECURITY": 0.9,
        "FABRICATION": 0.8,
        "VERIFICATION": 0.8,
        "SWARM": 0.7,
        "MEMORY": 0.7,
        "EXPERIENCE": 0.6,
    }

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: CortexMetrics,
    ) -> dict[str, Any] | None:
        if subagent.fitness >= 80.0:
            return None

        density_bonus = min(0.5, metrics.fact_density / 200.0)
        domain = sovereign.domain_id.split("_")[0]
        weight = self.DOMAIN_WEIGHTS.get(domain, 0.5) + density_bonus

        heuristic_key = f"hgt_{domain.lower()}_{int(time.time())}"
        subagent.mutation.parameters[heuristic_key] = weight * 100
        fitness_boost = weight * 5.0
        subagent.fitness += fitness_boost

        subagent.mutation.record_change(
            f"HGT: {heuristic_key} (w={weight:.2f}, +{fitness_boost:.2f})"
        )
        return {
            "strategy": "HeuristicInjection",
            "domain": domain,
            "weight": weight,
            "fitness_boost": fitness_boost,
        }


class BridgeImportStrategy:
    """
    Margulis (1970) — Endosymbiosis / Symbiotic Gene Transfer.
    Cross-domain knowledge bridging when fitness gap is large.
    """

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: CortexMetrics,
    ) -> dict[str, Any] | None:
        best = sovereign.get_best_subagent()
        worst = sovereign.get_worst_subagent()
        if not best or not worst or best.agent_id == worst.agent_id:
            return None
        if subagent.agent_id != worst.agent_id:
            return None

        gap = best.fitness - worst.fitness
        if gap <= 30.0:
            return None

        multiplier = 0.1 + 0.15 * metrics.bridge_score
        delta_fitness = gap * multiplier
        subagent.mutation.parameters.update(best.mutation.parameters)
        subagent.fitness += delta_fitness

        subagent.mutation.record_change(f"BridgeImport from {best.agent_id}: +{delta_fitness:.2f}")
        return {
            "strategy": "BridgeImport",
            "gap": gap,
            "multiplier": multiplier,
            "delta_fitness": delta_fitness,
            "source": best.agent_id,
        }


class AdversarialStressStrategy:
    """
    Van Valen (1973) — Red Queen Hypothesis.
    Controlled chaos injection for high-fitness agents to test resilience.
    """

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: CortexMetrics,
    ) -> dict[str, Any] | None:
        if subagent.fitness <= 100.0:
            return None

        p_queen = 0.1 + 0.5 * min(1.0, max(0.0, metrics.fitness_delta))
        if random.random() > p_queen:
            return None

        stress_hit = random.uniform(1.0, 5.0)
        new_fitness = subagent.fitness - stress_hit

        if new_fitness >= 100.0:
            subagent.fitness = new_fitness + 3.0
            subagent.mutation.record_change(f"RedQueen survived: -{stress_hit:.2f} +3.0 bonus")
            return {
                "strategy": "AdversarialStress",
                "result": "survived",
                "stress_hit": stress_hit,
                "resilience_bonus": 3.0,
                "p_queen": round(p_queen, 3),
            }
        else:
            subagent.fitness = max(0.0, new_fitness)
            subagent.mutation.record_change(f"RedQueen failed: fitness->{new_fitness:.2f}")
            return {
                "strategy": "AdversarialStress",
                "result": "failed",
                "stress_hit": stress_hit,
                "new_fitness": new_fitness,
                "p_queen": round(p_queen, 3),
            }


class EntropyReductionStrategy:
    """
    Kimura (1968) — Neutral Theory / Genetic Drift Correction.
    Axiom 12 (ψWitness Passive Observation) compliance.
    """

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: CortexMetrics,
    ) -> dict[str, Any] | None:
        if subagent.generation < 5 or subagent.fitness <= 50.0:
            return None

        entropy_ratio = subagent.generation / (subagent.fitness - 50.0)
        if entropy_ratio <= 20.0:
            return None

        original_len = len(subagent.mutation.history_log)
        subagent.mutation.history_log = [
            f"[COMPRESSED] {original_len} generations -> entropy purge"
        ]
        subagent.mutation.entropy_resistance = 1.0
        subagent.fitness += 2.0

        cortex_metrics.record_mutation(subagent.mutation, sovereign.domain_id)

        return {
            "strategy": "EntropyReduction",
            "entropy_ratio": entropy_ratio,
            "compressed_gens": original_len,
            "simplification_bonus": 2.0,
            "axiom_12_compliant": True,
        }


class CrossoverRecombinationStrategy:
    """
    Maynard Smith (1978) — Evolution of Sex / Recombination.
    High-variance recombination when fitness variance justifies cost.
    """

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: CortexMetrics,
    ) -> dict[str, Any] | None:
        best = sovereign.get_best_subagent()
        worst = sovereign.get_worst_subagent()
        if not best or not worst:
            return None

        gap = best.fitness - worst.fitness
        if gap <= 15.0 or subagent.fitness >= 70.0:
            return None

        delta = min(5.0, gap * 0.4)
        boost = delta * metrics.health_score

        for key, value in best.mutation.parameters.items():
            if random.random() > 0.5:
                subagent.mutation.parameters[key] = value

        subagent.fitness += boost
        subagent.mutation.record_change(f"Crossover with {best.agent_id}: +{boost:.2f}")
        return {
            "strategy": "CrossoverRecombination",
            "partner": best.agent_id,
            "gap": gap,
            "fitness_boost": boost,
        }


class StagnationBreakerStrategy:
    """
    Gould & Eldredge (1972) — Punctuated Equilibrium.
    Disrupts local optima when stasis is detected over a 5-mutation window.
    """

    STAGNATION_WINDOW: int = 5
    STAGNATION_THRESHOLD: float = 0.5
    _CIRCUIT_BREAKER_FITNESS: float = 80.0

    def __init__(self) -> None:
        self._history: dict[str, list[float]] = {}

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: CortexMetrics,
    ) -> dict[str, Any] | None:
        if subagent.fitness <= self._CIRCUIT_BREAKER_FITNESS:
            return None

        aid = subagent.agent_id
        hist = self._history.setdefault(aid, [])
        hist.append(subagent.fitness)

        if len(hist) > self.STAGNATION_WINDOW:
            hist.pop(0)

        if len(hist) < self.STAGNATION_WINDOW:
            return None

        deltas = [abs(hist[i] - hist[i - 1]) for i in range(1, len(hist))]
        if not all(d < self.STAGNATION_THRESHOLD for d in deltas):
            return None

        shock = max(-3.0, min(8.0, metrics.fitness_delta * 1.5 + random.uniform(-1.0, 2.0)))
        prev_fitness = subagent.fitness
        subagent.fitness = max(0.0, subagent.fitness + shock)
        self._history[aid] = [subagent.fitness]

        subagent.mutation.record_change(f"Punctuation shock: {shock:+.2f}")
        return {
            "strategy": "StagnationBreaker",
            "shock": shock,
            "stasis_window": self.STAGNATION_WINDOW,
            "previous_fitness": prev_fitness,
            "circuit_breaker": False,
        }


# ==============================================================================
# CORTEX EVOLUTION ENGINE ORCHESTRATOR
# ==============================================================================


class CortexEvolutionEngine:
    """
    Main orchestrator for CORTEX Phase 2 (v3) Continuous Improvement Engine.
    Implements the strategy chain and metric synchronization.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.metrics_backend = CortexMetrics(db_path)
        self.strategies: list[ImprovementStrategy] = [
            ParameterTuningStrategy(),
            PruneDeadPathStrategy(),
            HeuristicInjectionStrategy(),
            BridgeImportStrategy(),
            AdversarialStressStrategy(),
            EntropyReductionStrategy(),
            CrossoverRecombinationStrategy(),
            StagnationBreakerStrategy(),
            ZeroPromptingEvolutionStrategy(),  # Axiom Ω₇
        ]
        self._evaluation_count = 0
        self._prev_avg_fitness: dict[str, float] = {}

    def _dm(self, domain_id: str, ttl_seconds: int = 60) -> DomainMetrics | None:
        return self.metrics_backend.get_metrics(domain_id, ttl_seconds)

    def inject_telemetry(self, domain_id: str, **kwargs: Any) -> None:
        metrics = self._dm(domain_id) or DomainMetrics(domain_id=domain_id)
        for key, value in kwargs.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)
        metrics.timestamp = time.time()
        self.metrics_backend.update_metrics(metrics)

    def evaluate_population(self, sovereign: SovereignAgent) -> list[dict[str, Any]]:
        metrics = self._dm(sovereign.domain_id) or DomainMetrics(domain_id=sovereign.domain_id)
        if not self._dm(sovereign.domain_id):
            self.metrics_backend.update_metrics(metrics)

        results: list[dict[str, Any]] = []

        for subagent in sovereign.subagents:
            if subagent.is_active:
                sub_results = self._apply_strategies_to(sovereign, subagent, metrics)
                results.extend(sub_results)
                if any("delta_fitness" in r or "fitness_boost" in r for r in sub_results):
                    self._refresh_fitness_delta(sovereign, metrics)

        self._evaluation_count += 1
        return results

    def _apply_strategies_to(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        applied: set[str] = set()
        for strategy in self.strategies:
            name = type(strategy).__name__
            if name in applied:
                continue
            try:
                result = strategy.evaluate(sovereign, subagent, metrics, self.metrics_backend)
                if result:
                    applied.add(name)
                    results.append(
                        {"agent_id": subagent.agent_id, "timestamp": time.time(), **result}
                    )
            except (ValueError, TypeError, AttributeError, RuntimeError) as exc:
                results.append({"agent_id": subagent.agent_id, "strategy": name, "error": str(exc)})
        return results

    def _refresh_fitness_delta(self, sovereign: SovereignAgent, metrics: DomainMetrics) -> None:
        active = [s.fitness for s in sovereign.subagents if s.is_active]
        if not active:
            return
        current_avg = sum(active) / len(active)
        domain = sovereign.domain_id
        prev_avg = self._prev_avg_fitness.get(domain, current_avg)
        metrics.fitness_delta = current_avg - prev_avg
        self._prev_avg_fitness[domain] = current_avg
        metrics.timestamp = time.time()
        self.metrics_backend.update_metrics(metrics)

    def get_system_status(self) -> dict[str, Any]:
        return {
            "evaluation_count": self._evaluation_count,
            "cached_domains": len(self.metrics_backend._cache),
            "strategies_active": len(self.strategies),
            "wal_mode": True,
            "ttl_seconds": 60,
        }
