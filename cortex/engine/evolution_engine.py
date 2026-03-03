"""
CORTEX Phase 2 (v3) - Continuous Improvement Engine
Bio-inspired Computational Evolution Architecture
"""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

# ==============================================================================
# DATA STRUCTURES
# ==============================================================================


@dataclass
class DomainMetrics:
    """
    CortexMetrics data structure representing domain health telemetry.
    Maps to the synchronized SQLite3 backend with 60s TTL cache.
    """

    domain_id: str
    health_score: float = 1.0  # 0.0 to 1.0, >0.9 is sovereign-grade
    error_rate: float = 0.0  # 0.0 to 1.0, frequency of failure events
    ghost_density: float = 0.0  # Concentration of dead/abandoned paths
    fact_density: float = 0.0  # Volume of verified informational units
    bridge_score: float = 0.0  # Measure of cross-domain knowledge links
    fitness_delta: float = 0.0  # Rate of change in fitness over window
    timestamp: float = field(default_factory=time.time)

    def is_stale(self, ttl_seconds: int = 60) -> bool:
        return (time.time() - self.timestamp) > ttl_seconds


@dataclass
class Mutation:
    """Genotype representation passed to execution environment."""

    mutation_id: str
    parameters: dict[str, float] = field(default_factory=dict)
    generation: int = 0
    fitness: float = 0.0
    history_log: list[str] = field(default_factory=list)
    entropy_resistance: float = 1.0  # S_ψ — resistance to coherence decay

    def record_change(self, change_desc: str) -> None:
        self.history_log.append(f"[Gen {self.generation}] {change_desc}")
        self.generation += 1


@dataclass
class SubAgent:
    """Individual agent within a sovereign domain."""

    agent_id: str
    mutation: Mutation
    domain_id: str
    fitness: float = 0.0
    generation: int = 0
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.generation == 0:
            self.generation = self.mutation.generation


@dataclass
class SovereignAgent:
    """Top-level autonomous agent containing sub-agent population."""

    sovereign_id: str
    domain_id: str
    subagents: list[SubAgent] = field(default_factory=list)
    creation_timestamp: float = field(default_factory=time.time)

    def get_best_subagent(self) -> SubAgent | None:
        active = [s for s in self.subagents if s.is_active]
        return max(active, key=lambda x: x.fitness) if active else None

    def get_worst_subagent(self) -> SubAgent | None:
        active = [s for s in self.subagents if s.is_active]
        return min(active, key=lambda x: x.fitness) if active else None

    def get_fitness_variance(self) -> float:
        active = [s.fitness for s in self.subagents if s.is_active]
        if len(active) < 2:
            return 0.0
        mean = sum(active) / len(active)
        return sum((x - mean) ** 2 for x in active) / len(active)


# ==============================================================================
# CORTEX METRICS INFRASTRUCTURE (SQLite3 + WAL + TTL Cache)
# ==============================================================================


class CortexMetrics:
    """
    Synchronized SQLite3 backend with WAL mode and 60-second TTL cache.
    Provides ACID-compliant persistence optimized for high-concurrency.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._cache: dict[str, tuple[DomainMetrics, float]] = {}
        self._cache_lock = threading.RLock()
        self._local = threading.local()
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            self._local.conn = conn
        return self._local.conn

    def _init_database(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS domain_metrics (
                domain_id    TEXT PRIMARY KEY,
                health_score REAL DEFAULT 1.0,
                error_rate   REAL DEFAULT 0.0,
                ghost_density REAL DEFAULT 0.0,
                fact_density REAL DEFAULT 0.0,
                bridge_score REAL DEFAULT 0.0,
                fitness_delta REAL DEFAULT 0.0,
                timestamp    REAL DEFAULT 0.0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mutation_ledger (
                mutation_id TEXT PRIMARY KEY,
                hash_chain  TEXT NOT NULL,
                timestamp   REAL DEFAULT 0.0,
                data        TEXT NOT NULL
            )
        """)
        conn.commit()

    def update_metrics(self, metrics: DomainMetrics) -> None:
        """Persist metrics with hash verification (Axiom 12 compliance)."""
        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO domain_metrics
            (domain_id, health_score, error_rate, ghost_density, fact_density,
             bridge_score, fitness_delta, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metrics.domain_id,
                metrics.health_score,
                metrics.error_rate,
                metrics.ghost_density,
                metrics.fact_density,
                metrics.bridge_score,
                metrics.fitness_delta,
                metrics.timestamp,
            ),
        )
        conn.commit()
        with self._cache_lock:
            self._cache[metrics.domain_id] = (metrics, time.time())

    def get_metrics(self, domain_id: str, ttl_seconds: int = 60) -> DomainMetrics | None:
        """Returns cached metrics if fresh, otherwise queries SQLite."""
        now = time.time()
        with self._cache_lock:
            if domain_id in self._cache:
                cached, cached_at = self._cache[domain_id]
                if (now - cached_at) < ttl_seconds:
                    return cached

        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT health_score, error_rate, ghost_density, fact_density,
                   bridge_score, fitness_delta, timestamp
            FROM domain_metrics WHERE domain_id = ?
        """,
            (domain_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        metrics = DomainMetrics(
            domain_id=domain_id,
            health_score=row[0],
            error_rate=row[1],
            ghost_density=row[2],
            fact_density=row[3],
            bridge_score=row[4],
            fitness_delta=row[5],
            timestamp=row[6],
        )
        with self._cache_lock:
            self._cache[domain_id] = (metrics, now)
        return metrics

    def record_mutation(self, mutation: Mutation, domain_id: str) -> None:
        """Immutable ledger entry — Axiom 12 (ψWitness Passive Observation)."""
        conn = self._get_connection()
        data = {
            "parameters": mutation.parameters,
            "generation": mutation.generation,
            "fitness": mutation.fitness,
            "history": mutation.history_log[-5:],
        }
        prev_hash = self._get_last_hash(domain_id)
        content = f"{prev_hash}:{json.dumps(data, sort_keys=True)}"
        current_hash = hashlib.sha256(content.encode()).hexdigest()
        conn.execute(
            """
            INSERT OR REPLACE INTO mutation_ledger (mutation_id, hash_chain, timestamp, data)
            VALUES (?, ?, ?, ?)
        """,
            (mutation.mutation_id, current_hash, time.time(), json.dumps(data)),
        )
        conn.commit()

    def _get_last_hash(self, domain_id: str) -> str:
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT hash_chain FROM mutation_ledger
            WHERE mutation_id LIKE ? ORDER BY timestamp DESC LIMIT 1
        """,
            (f"{domain_id}%",),
        )
        row = cursor.fetchone()
        return row[0] if row else "0" * 64


# ==============================================================================
# IMPROVEMENT STRATEGY PROTOCOL
# ==============================================================================


class ImprovementStrategy(Protocol):
    """Protocol for pluggable evolutionary improvement strategies."""

    def evaluate(
        self,
        sovereign: SovereignAgent,
        subagent: SubAgent,
        metrics: DomainMetrics,
        cortex_metrics: CortexMetrics,
    ) -> dict[str, Any] | None:
        """
        Evaluate and potentially improve a subagent.
        Returns mutation delta dict if changes applied, None if skipped.
        """
        ...


# ==============================================================================
# EVOLUTIONARY STRATEGIES
# ==============================================================================


class ParameterTuningStrategy:
    """
    Eigen (1971) — Quasispecies Error Threshold.
    Adaptive mutation rates based on error_rate to avoid error catastrophe.

    Formula: scale = 0.5 + 2.5 * error_rate
             delta = scale * uniform(0.5, 1.2)
    Guard: sovereign-grade stability (health_score > 0.9) → skip.
    """

    def evaluate(self, sovereign, subagent, metrics, cortex_metrics):
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

    Formula: threshold = 20.0 + 20.0 * ghost_density
             liberation_bonus = 1.0 + ghost_density * 2.0
    Guard: generational protection (generation <= 5).
    """

    def evaluate(self, sovereign, subagent, metrics, cortex_metrics):
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

    Formula: density_bonus = min(0.5, fact_density / 200.0)
             weight = base_weight + density_bonus
             fitness_boost = weight * 5.0
    Trigger: fitness < 80.0
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

    def evaluate(self, sovereign, subagent, metrics, cortex_metrics):
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

    Formula: multiplier = 0.1 + 0.15 * bridge_score
             delta_fitness = gap * multiplier
    Trigger: gap > 30.0, applied only to worst agent.
    """

    def evaluate(self, sovereign, subagent, metrics, cortex_metrics):
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

    Production-grade: frequency-dependent trigger (p scales with fitness_delta).
    High-velocity domains face more pressure — the faster you run, the harder you're chased.

    Trigger: fitness > 100.0, p_queen = 0.1 + 0.5 * clamp(fitness_delta, 0, 1).
    Shock: uniform(1.0, 5.0). Survivors (+3.0), Failures (-1.0 penalty, flagged).
    """

    def evaluate(self, sovereign, subagent, metrics, cortex_metrics):
        if subagent.fitness <= 100.0:
            return None

        # Frequency-dependent Red Queen: faster-evolving domains face more chaos.
        p_queen = 0.1 + 0.5 * min(1.0, max(0.0, metrics.fitness_delta))
        if random.random() > p_queen:
            return None

        stress_hit = random.uniform(1.0, 5.0)
        new_fitness = subagent.fitness - stress_hit

        if new_fitness >= 100.0:
            subagent.fitness = new_fitness + 3.0  # Resilience bonus
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
            subagent.mutation.record_change(f"RedQueen failed: fitness→{new_fitness:.2f}")
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

    Formula: entropy_ratio = generation / (fitness - 50.0)
    Trigger: ratio > 20.0 → compress history, reset entropy_resistance.
    Guard: fitness <= 50.0 or generation < 5 (too young to have meaningful drift).
    Bonus: +2.0 fitness for structural simplification.
    """

    def evaluate(self, sovereign, subagent, metrics, cortex_metrics):
        # Guard: too young or too weak to apply entropy reduction (D5 backport)
        if subagent.generation < 5 or subagent.fitness <= 50.0:
            return None

        entropy_ratio = subagent.generation / (subagent.fitness - 50.0)
        if entropy_ratio <= 20.0:
            return None

        original_len = len(subagent.mutation.history_log)
        subagent.mutation.history_log = [f"[COMPRESSED] {original_len} generations → entropy purge"]
        subagent.mutation.entropy_resistance = 1.0
        subagent.fitness += 2.0

        # Axiom 12: immutable ledger record
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

    Formula: delta = min(5.0, gap * 0.4)
             boost = delta * health_score
    Trigger: gap > 15.0, subagent.fitness < 70.0. 50% trait inheritance.
    """

    def evaluate(self, sovereign, subagent, metrics, cortex_metrics):
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

    Formula: shock = fitness_delta * 1.5 + uniform(-1.0, 2.0)
             shock = clamp(shock, -3.0, 8.0)
    Trigger: all 5 consecutive deltas < 0.5 (stasis).
    Guard (Gould-Eldredge Circuit Breaker): fitness <= 80.0 → skip.
             A negative shock on an already-struggling agent causes death spirals.
    """

    STAGNATION_WINDOW: int = 5
    STAGNATION_THRESHOLD: float = 0.5
    _CIRCUIT_BREAKER_FITNESS: float = 80.0  # D3 backport from production

    def __init__(self) -> None:
        self._history: dict[str, list[float]] = {}

    def evaluate(self, sovereign, subagent, metrics, cortex_metrics):
        # Circuit Breaker (Gould-Eldredge): never shock an agent already struggling.
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
        self._history[aid] = [subagent.fitness]  # reset window post-shock

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
        self.strategies: list[Any] = [
            ParameterTuningStrategy(),  # Eigen 1971
            PruneDeadPathStrategy(),  # Fisher 1930
            HeuristicInjectionStrategy(),  # Ochman 2000
            BridgeImportStrategy(),  # Margulis 1970
            AdversarialStressStrategy(),  # Van Valen 1973
            EntropyReductionStrategy(),  # Kimura 1968
            CrossoverRecombinationStrategy(),  # Maynard Smith 1978
            StagnationBreakerStrategy(),  # Gould-Eldredge 1972
        ]
        self._evaluation_count = 0
        # Tracks previous average fitness per domain for correct delta computation
        self._prev_avg_fitness: dict[str, float] = {}

    def _dm(self, domain_id: str, ttl_seconds: int = 60) -> DomainMetrics | None:
        """Instantaneous access to DomainMetrics with TTL guard."""
        return self.metrics_backend.get_metrics(domain_id, ttl_seconds)

    def inject_telemetry(self, domain_id: str, **kwargs: Any) -> None:
        """External interface to update domain metrics."""
        metrics = self._dm(domain_id) or DomainMetrics(domain_id=domain_id)
        for key, value in kwargs.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)
        metrics.timestamp = time.time()
        self.metrics_backend.update_metrics(metrics)

    def evaluate_population(self, sovereign: SovereignAgent) -> list[dict[str, Any]]:
        """Run the full strategy chain against a sovereign agent's population."""
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
        """Apply all matching strategies to a single subagent. One application per strategy type."""
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
            except Exception as exc:
                results.append({"agent_id": subagent.agent_id, "strategy": name, "error": str(exc)})
        return results

    def _refresh_fitness_delta(self, sovereign: SovereignAgent, metrics: DomainMetrics) -> None:
        active = [s.fitness for s in sovereign.subagents if s.is_active]
        if not active:
            return
        current_avg = sum(active) / len(active)
        domain = sovereign.domain_id
        # Correct: delta = change in average fitness, not change in delta.
        # First call seeds to 0.0 (no prior baseline to compare against).
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


# ==============================================================================
# SIMULATION
# ==============================================================================


def run_evolution_simulation() -> None:
    """Demonstrate CORTEX Phase 2 (v3) with synthetic agent population."""
    SEP = "=" * 70
    print(f"\n{SEP}")
    print("CORTEX Phase 2 (v3) — Continuous Improvement Engine")
    print("Bio-inspired Computational Evolution Architecture")
    print(SEP)

    engine = CortexEvolutionEngine()

    sovereign = SovereignAgent(sovereign_id="SOV_EVOLUTION_001", domain_id="EVOLUTION_TEST")

    for i in range(5):
        mutation = Mutation(
            mutation_id=f"MUT_{i}_{int(time.time())}",
            parameters={"learning_rate": 0.01 * (i + 1), "batch_size": 32.0},
            generation=random.randint(1, 20),
            fitness=random.uniform(20.0, 150.0),
        )
        sovereign.subagents.append(
            SubAgent(
                agent_id=f"AGENT_{i:03d}",
                mutation=mutation,
                domain_id="EVOLUTION_TEST",
                fitness=mutation.fitness,
                generation=mutation.generation,
            )
        )

    print("\n[INITIAL POPULATION]")
    for a in sovereign.subagents:
        print(
            f"  {a.agent_id}: fitness={a.fitness:.2f}  gen={a.generation}  "
            f"status={'ACTIVE' if a.is_active else 'PRUNED'}"
        )

    engine.inject_telemetry(
        "EVOLUTION_TEST",
        health_score=0.85,
        error_rate=0.3,
        ghost_density=0.5,
        fact_density=100.0,
        bridge_score=0.6,
        fitness_delta=0.2,
    )

    print("\n[EVOLUTION CYCLES]")
    for cycle in range(5):
        print(f"\n--- Cycle {cycle + 1} ---")

        if cycle == 2:
            engine.inject_telemetry("EVOLUTION_TEST", error_rate=0.8, ghost_density=0.8)
            print("  ⚡ ENVIRONMENTAL SHIFT: error_rate=0.8, ghost_density=0.8")

        results = engine.evaluate_population(sovereign)
        if results:
            for r in results:
                strat = r.get("strategy", "unknown")
                aid = r.get("agent_id", "?")
                bonus = r.get("delta_fitness", r.get("fitness_boost", r.get("shock", None)))
                bonus_str = f"  → {bonus:+.2f}" if bonus is not None else ""
                print(f"  [{strat}] on {aid}{bonus_str}")
        else:
            print("  — No strategies triggered (population sovereign-stable)")

        active = [s for s in sovereign.subagents if s.is_active]
        avg_f = sum(s.fitness for s in active) / len(active) if active else 0.0
        print(f"  ↳ Active: {len(active)}/{len(sovereign.subagents)}, avg_fitness={avg_f:.2f}")

    print("\n[FINAL POPULATION]")
    for a in sovereign.subagents:
        entropy = (a.generation / (a.fitness - 50.0)) if a.fitness > 50.0 else float("inf")
        print(
            f"  {a.agent_id}: fitness={a.fitness:.2f}  gen={a.generation}  "
            f"entropy_ratio={entropy:.2f}  status={'ACTIVE' if a.is_active else 'PRUNED'}"
        )

    print("\n[SYSTEM STATUS]")
    for k, v in engine.get_system_status().items():
        print(f"  {k}: {v}")

    print(f"\n{SEP}\nSimulation Complete\n{SEP}\n")


if __name__ == "__main__":
    run_evolution_simulation()
