"""SICA Autonomy — Self-Directed Operation Capabilities.

Five autonomy primitives that transform SICA from a reactive agent
into a self-governing cognitive architecture:

1. AutonomousTick — proactive self-diagnostics without messages
2. SpeculativeFork — parallel strategy exploration on hard failures
3. TraceSynthesizer — learn new heuristics from trace patterns
4. MetaMetaController — active self-correction of the meta-level
5. AdaptiveRetry — dynamic retry budgets based on failure type
"""

from __future__ import annotations

import copy
import logging
import random
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from cortex.sica.meta_level import FailureClass, MetaAction, MetaJudgment, MetaLevel
from cortex.sica.object_level import ExecutionTrace, ObjectLevel, StepOutcome
from cortex.sica.strategy import Heuristic, SearchStrategy, StrategyGenome

logger = logging.getLogger("cortex.sica.autonomy")


# ═══════════════════════════════════════════════════════════════════
# 1. SPECULATIVE FORK — Parallel strategy exploration
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ForkResult:
    """Result of a speculative fork evaluation."""

    fork_id: int
    genome_hash: str
    fitness: float
    mutations_applied: list[str]
    outcome: str  # "adopted" | "discarded"


class SpeculativeFork:
    """Try N parallel strategy mutations and pick the best.

    When the agent hits a hard failure, instead of making a single
    mutation and hoping it works, fork the strategy into N variants,
    evaluate each against recent traces, and adopt the fittest.

    This is the agent's equivalent of "brainstorming multiple approaches
    before committing to one."
    """

    def __init__(self, n_forks: int = 3) -> None:
        self._n_forks = n_forks
        self._fork_history: list[ForkResult] = []

    @property
    def fork_history(self) -> list[ForkResult]:
        return list(self._fork_history)

    def speculate(
        self,
        strategy: SearchStrategy,
        judgment: MetaJudgment,
        recent_traces: list[ExecutionTrace],
    ) -> SearchStrategy:
        """Fork strategy N ways, evaluate, adopt the best.

        Each fork applies a different random mutation.
        Fitness is evaluated by replaying recent traces mentally
        (checking if heuristic weights would have led to better decisions).

        Returns the best forked strategy (or original if no improvement).
        """
        if not judgment.requires_strategy_mutation:
            return strategy

        original_fitness = strategy.current_fitness
        candidates: list[tuple[SearchStrategy, float, list[str]]] = []

        for _i in range(self._n_forks):
            forked = strategy.fork()
            mutations = self._apply_random_mutations(forked, judgment)
            fitness = self._evaluate_fork(forked, recent_traces)
            candidates.append((forked, fitness, mutations))

        # Sort by fitness descending
        candidates.sort(key=lambda c: c[1], reverse=True)
        best_fork, best_fitness, best_mutations = candidates[0]

        # Record all fork results
        for i, (f, fitness, muts) in enumerate(candidates):
            adopted = i == 0 and best_fitness > original_fitness
            self._fork_history.append(
                ForkResult(
                    fork_id=i,
                    genome_hash=f.genome.genome_hash,
                    fitness=round(fitness, 4),
                    mutations_applied=muts,
                    outcome="adopted" if adopted else "discarded",
                )
            )

        if best_fitness > original_fitness:
            logger.info(
                "SpeculativeFork: adopting fork (fitness %.3f → %.3f, mutations=%s)",
                original_fitness,
                best_fitness,
                best_mutations,
            )
            return best_fork
        else:
            logger.info(
                "SpeculativeFork: no improvement found (best=%.3f, current=%.3f)",
                best_fitness,
                original_fitness,
            )
            return strategy

    def _apply_random_mutations(
        self,
        strategy: SearchStrategy,
        judgment: MetaJudgment,
    ) -> list[str]:
        """Apply 1-3 random mutations to a forked strategy."""
        mutations_applied: list[str] = []
        n_mutations = random.randint(1, 3)
        genome = strategy.genome

        for _ in range(n_mutations):
            action = random.choice(
                [
                    "amplify_random",
                    "attenuate_random",
                    "adjust_exploration",
                    "swap_tool_priority",
                ]
            )

            if action == "amplify_random" and genome.heuristics:
                h = random.choice(genome.heuristics)
                factor = random.uniform(1.1, 1.5)
                strategy.mutate_amplify(h.name, reason="speculative fork", factor=factor)
                mutations_applied.append(f"amplify:{h.name}")

            elif action == "attenuate_random" and genome.heuristics:
                h = random.choice(genome.heuristics)
                factor = random.uniform(0.4, 0.8)
                strategy.mutate_attenuate(h.name, reason="speculative fork", factor=factor)
                mutations_applied.append(f"attenuate:{h.name}")

            elif action == "adjust_exploration":
                delta = random.uniform(-0.2, 0.2)
                new_rate = max(0.05, min(0.9, genome.exploration_rate + delta))
                strategy.mutate_exploration_rate(new_rate, reason="speculative fork")
                mutations_applied.append(f"exploration:{new_rate:.2f}")

            elif action == "swap_tool_priority" and len(genome.tool_priority) > 1:
                i, j = random.sample(range(len(genome.tool_priority)), 2)
                genome.tool_priority[i], genome.tool_priority[j] = (
                    genome.tool_priority[j],
                    genome.tool_priority[i],
                )
                mutations_applied.append(f"swap_tools:{i}<>{j}")

        return mutations_applied

    def _evaluate_fork(
        self,
        strategy: SearchStrategy,
        recent_traces: list[ExecutionTrace],
    ) -> float:
        """Evaluate a forked strategy against recent trace history.

        Uses a simplified fitness function:
        - Heuristics that were activated on successful traces get bonus
        - Heuristics that were activated on failed traces get penalty
        - Exploration rate is penalized if too extreme
        """
        if not recent_traces:
            return strategy.current_fitness

        score = strategy.current_fitness * 0.5  # Base: intrinsic fitness
        heuristic_names = {h.name for h in strategy.genome.heuristics}

        for trace in recent_traces:
            activated = set(trace.heuristics_activated)
            overlap = activated & heuristic_names

            if trace.final_outcome == StepOutcome.SUCCESS:
                score += 0.1 * len(overlap)  # Reward overlap with success traces
            else:
                score -= 0.05 * len(overlap)  # Penalize overlap with failure traces

        # Penalize extreme exploration rates
        er = strategy.genome.exploration_rate
        if er < 0.1 or er > 0.8:
            score -= 0.1

        return max(0.0, min(1.0, score))


# ═══════════════════════════════════════════════════════════════════
# 2. TRACE SYNTHESIZER — Learn heuristics from patterns
# ═══════════════════════════════════════════════════════════════════


class TraceSynthesizer:
    """Analyze accumulated traces to synthesize new heuristics.

    Instead of only using hardcoded heuristic templates, this module
    discovers emergent patterns from the agent's own execution history
    and proposes new heuristics.

    Patterns detected:
    - Tools that consistently succeed together → "tool_combo" heuristic
    - Time-of-day performance variations → "temporal_bias" heuristic
    - Task-type clustering → "task_specialization" heuristic
    """

    def __init__(self, min_traces: int = 10) -> None:
        self._min_traces = min_traces

    def synthesize(
        self,
        traces: list[ExecutionTrace],
        existing_heuristics: list[Heuristic],
    ) -> list[Heuristic]:
        """Analyze traces and propose new heuristics.

        Only proposes heuristics that don't already exist.
        """
        if len(traces) < self._min_traces:
            return []

        existing_names = {h.name for h in existing_heuristics}
        proposals: list[Heuristic] = []

        # Pattern 1: Tool combos that correlate with success
        combo_h = self._detect_tool_combos(traces)
        if combo_h and combo_h.name not in existing_names:
            proposals.append(combo_h)

        # Pattern 2: Failure-preceding actions (anti-patterns)
        anti_h = self._detect_anti_patterns(traces)
        if anti_h and anti_h.name not in existing_names:
            proposals.append(anti_h)

        # Pattern 3: Optimal step count
        depth_h = self._detect_optimal_depth(traces)
        if depth_h and depth_h.name not in existing_names:
            proposals.append(depth_h)

        if proposals:
            logger.info(
                "TraceSynthesizer: proposed %d new heuristics from %d traces: %s",
                len(proposals),
                len(traces),
                [h.name for h in proposals],
            )

        return proposals

    def _detect_tool_combos(self, traces: list[ExecutionTrace]) -> Heuristic | None:
        """Find tool combinations that correlate with success."""
        success_tools: Counter[str] = Counter()
        failure_tools: Counter[str] = Counter()

        for trace in traces:
            tools = tuple(sorted(trace.tools_used))
            key = "+".join(tools) if tools else ""
            if not key:
                continue
            if trace.final_outcome == StepOutcome.SUCCESS:
                success_tools[key] += 1
            else:
                failure_tools[key] += 1

        if not success_tools:
            return None

        best_combo, count = success_tools.most_common(1)[0]
        fail_count = failure_tools.get(best_combo, 0)

        if count >= 3 and count > fail_count * 2:
            return Heuristic(
                name=f"prefer_combo_{best_combo.replace('+', '_')}",
                description=(
                    f"Tool combination [{best_combo}] succeeded {count} times "
                    f"vs {fail_count} failures. Prefer this combination."
                ),
                weight=0.6,
            )
        return None

    def _detect_anti_patterns(self, traces: list[ExecutionTrace]) -> Heuristic | None:
        """Find actions that consistently precede failures."""
        pre_failure_actions: Counter[str] = Counter()

        for trace in traces:
            if trace.final_outcome != StepOutcome.FAILURE:
                continue
            # Look at action before first failure
            for i, step in enumerate(trace.steps):
                if step.outcome == StepOutcome.FAILURE and i > 0:
                    prev = trace.steps[i - 1]
                    pre_failure_actions[prev.action] += 1
                    break

        if not pre_failure_actions:
            return None

        worst_action, count = pre_failure_actions.most_common(1)[0]
        if count >= 3:
            return Heuristic(
                name=f"avoid_before_failure_{worst_action.replace(':', '_')}",
                description=(
                    f"Action '{worst_action}' preceded failure {count} times. "
                    f"Consider alternative approaches when this action is next."
                ),
                weight=0.5,
            )
        return None

    def _detect_optimal_depth(self, traces: list[ExecutionTrace]) -> Heuristic | None:
        """Find the optimal number of steps for success."""
        success_depths = [t.step_count for t in traces if t.final_outcome == StepOutcome.SUCCESS]
        failure_depths = [t.step_count for t in traces if t.final_outcome == StepOutcome.FAILURE]

        if len(success_depths) < 5:
            return None

        avg_success = sum(success_depths) / len(success_depths)
        avg_failure = sum(failure_depths) / len(failure_depths) if failure_depths else avg_success

        # If failures consistently have more steps, suggest depth limit
        if avg_failure > avg_success * 1.5 and avg_failure > 4:
            optimal = int(avg_success + 1)
            return Heuristic(
                name="depth_limiter",
                description=(
                    f"Successful tasks average {avg_success:.1f} steps, "
                    f"failures average {avg_failure:.1f}. Cap execution at "
                    f"{optimal} steps and re-evaluate."
                ),
                weight=0.5,
            )
        return None


# ═══════════════════════════════════════════════════════════════════
# 3. META-META CONTROLLER — Active meta-level self-correction
# ═══════════════════════════════════════════════════════════════════


@dataclass
class MetaMetaDiagnosis:
    """Diagnosis of the meta-level's own performance."""

    pattern: str
    severity: str  # "warning" | "critical"
    action_taken: str
    details: str
    timestamp: float = field(default_factory=time.monotonic)


class MetaMetaController:
    """Active self-correction of the meta-level.

    Upgrades _check_meta_patterns from passive logging to active control:
    - Tunnel vision → force diagnosis diversity
    - Stale mutations → reset mutation approach
    - Blind spots → inject diagnostic heuristics
    - Overconfidence → calibrate judgment confidence

    This closes the Nelson-Narens loop recursively:
    the controller monitors the monitor.
    """

    def __init__(self) -> None:
        self._diagnosis_log: list[MetaMetaDiagnosis] = []
        self._intervention_count = 0

    @property
    def diagnosis_log(self) -> list[MetaMetaDiagnosis]:
        return list(self._diagnosis_log)

    def check_and_correct(
        self,
        meta_level: MetaLevel,
        strategy: SearchStrategy,
    ) -> list[MetaMetaDiagnosis]:
        """Run all meta-meta checks and apply corrections.

        Returns list of diagnoses (and actions taken).
        """
        diagnoses: list[MetaMetaDiagnosis] = []

        d = self._check_tunnel_vision(meta_level, strategy)
        if d:
            diagnoses.append(d)

        d = self._check_mutation_stagnation(meta_level, strategy)
        if d:
            diagnoses.append(d)

        d = self._check_judgment_confidence_drift(meta_level)
        if d:
            diagnoses.append(d)

        d = self._check_exploration_convergence(strategy)
        if d:
            diagnoses.append(d)

        self._diagnosis_log.extend(diagnoses)
        return diagnoses

    def _check_tunnel_vision(
        self,
        meta_level: MetaLevel,
        strategy: SearchStrategy,
    ) -> MetaMetaDiagnosis | None:
        """Detect and correct diagnostic tunnel vision.

        If all recent judgments classify the same failure type,
        force the meta-level to consider alternative diagnoses
        by injecting a novelty-seeking heuristic.
        """
        recent = meta_level.judgment_history[-10:]
        if len(recent) < 5:
            return None

        classes = [j.failure_class for j in recent if j.failure_class is not None]
        if not classes or len(set(classes)) > 1:
            return None

        dominant = classes[0]

        # ACTIVE CORRECTION: increase exploration to break out
        old_rate = strategy.genome.exploration_rate
        new_rate = min(0.8, old_rate + 0.2)
        strategy.mutate_exploration_rate(
            new_rate,
            reason=f"Meta-meta: breaking tunnel vision on {dominant.value}",
        )
        self._intervention_count += 1

        return MetaMetaDiagnosis(
            pattern="tunnel_vision",
            severity="warning",
            action_taken=f"exploration_rate {old_rate:.2f}→{new_rate:.2f}",
            details=f"All {len(classes)} recent judgments classified as {dominant.value}",
        )

    def _check_mutation_stagnation(
        self,
        meta_level: MetaLevel,
        strategy: SearchStrategy,
    ) -> MetaMetaDiagnosis | None:
        """Detect and correct mutation stagnation.

        If mutations aren't improving fitness, try a radically
        different approach: reset a random heuristic's weight
        to 0.5 (neutral) to break the local optimum.
        """
        mutations = strategy.mutation_log[-8:]
        if len(mutations) < 5:
            return None

        # Check if all recent mutations had non-positive deltas
        deltas = [m.fitness_delta for m in mutations if m.fitness_delta is not None]
        if not deltas or any(d > 0 for d in deltas):
            return None

        # ACTIVE CORRECTION: reset a random heuristic to neutral
        heuristics = strategy.genome.active_heuristics
        if not heuristics:
            return None

        target = random.choice(heuristics)
        old_weight = target.weight
        target.weight = 0.5
        target.activation_count = 0
        target.success_count = 0
        self._intervention_count += 1

        return MetaMetaDiagnosis(
            pattern="mutation_stagnation",
            severity="critical",
            action_taken=f"reset {target.name} weight {old_weight:.3f}→0.500",
            details=f"Last {len(deltas)} mutations had non-positive fitness delta",
        )

    def _check_judgment_confidence_drift(
        self,
        meta_level: MetaLevel,
    ) -> MetaMetaDiagnosis | None:
        """Detect systematic confidence miscalibration in judgments.

        If the meta-level is consistently overconfident (>0.8) but
        its recommendations don't improve outcomes, flag it.
        """
        recent = meta_level.judgment_history[-15:]
        if len(recent) < 10:
            return None

        high_conf = [j for j in recent if j.confidence > 0.8]
        if len(high_conf) < 7:
            return None

        # Check if high-confidence judgments actually led to improvements
        # (rough proxy: were there meta-failures despite high confidence?)
        meta_fails_with_high_conf = sum(1 for j in high_conf if j.is_meta_failure)

        if meta_fails_with_high_conf >= 3:
            self._intervention_count += 1
            return MetaMetaDiagnosis(
                pattern="confidence_drift",
                severity="warning",
                action_taken="flagged for confidence recalibration",
                details=(
                    f"{meta_fails_with_high_conf}/{len(high_conf)} high-confidence "
                    f"judgments were meta-failures"
                ),
            )
        return None

    def _check_exploration_convergence(
        self,
        strategy: SearchStrategy,
    ) -> MetaMetaDiagnosis | None:
        """Detect premature exploration convergence.

        If exploration rate has been decreasing monotonically and
        is now very low, force a bump to prevent premature convergence.
        """
        genome = strategy.genome
        if genome.exploration_rate > 0.15:
            return None

        # Check if all heuristic weights have converged (low variance)
        weights = [h.weight for h in genome.active_heuristics]
        if not weights or len(weights) < 3:
            return None

        mean_w = sum(weights) / len(weights)
        variance = sum((w - mean_w) ** 2 for w in weights) / len(weights)

        if variance < 0.01:  # Very low diversity
            old_rate = genome.exploration_rate
            new_rate = 0.4  # Force significant exploration
            strategy.mutate_exploration_rate(
                new_rate,
                reason="Meta-meta: breaking premature convergence",
            )
            self._intervention_count += 1

            return MetaMetaDiagnosis(
                pattern="premature_convergence",
                severity="critical",
                action_taken=f"exploration_rate {old_rate:.2f}→{new_rate:.2f}",
                details=f"Weight variance={variance:.4f}, all heuristics converged",
            )
        return None


# ═══════════════════════════════════════════════════════════════════
# 4. ADAPTIVE RETRY — Dynamic retry budgets
# ═══════════════════════════════════════════════════════════════════


class AdaptiveRetry:
    """Dynamic retry budgets based on failure classification.

    Instead of fixed max_retries=3, adapt based on:
    - Meta-failures get more retries (strategy was mutated, worth trying again)
    - Object-failures with same error get fewer (likely systematic)
    - Constitutional aborts get zero retries
    - First-time failure types get extra budget (might be transient)
    """

    def __init__(self, base_budget: int = 3) -> None:
        self._base = base_budget
        self._seen_failure_classes: Counter[str] = Counter()

    def compute_budget(self, judgment: MetaJudgment) -> int:
        """Compute the retry budget for a given judgment."""
        if judgment.constitutional_verdict and judgment.constitutional_verdict.abort_needed:
            return 0  # No retries on constitutional abort

        fc = judgment.failure_class
        if fc is None:
            return self._base

        fc_key = fc.value
        self._seen_failure_classes[fc_key] += 1
        times_seen = self._seen_failure_classes[fc_key]

        if judgment.is_meta_failure:
            # Meta-failures: strategy was mutated, give it room
            budget = self._base + 2
            # But diminish if this failure class keeps recurring
            budget = max(1, budget - (times_seen // 3))
        else:
            # Object-failures: diminish faster for known patterns
            budget = max(1, self._base - (times_seen // 2))

        # First-time failure types get a bonus
        if times_seen == 1:
            budget += 1

        return min(budget, self._base + 3)  # Hard cap

    def reset_for_class(self, failure_class: str) -> None:
        """Reset the counter for a failure class (e.g., after a success)."""
        if failure_class in self._seen_failure_classes:
            del self._seen_failure_classes[failure_class]


# ═══════════════════════════════════════════════════════════════════
# 5. AUTONOMOUS TICK — Proactive self-diagnostics
# ═══════════════════════════════════════════════════════════════════


class AutonomousTick:
    """Proactive self-diagnostic cycle.

    Runs during idle periods (no messages) to:
    - Prune dead heuristics
    - Synthesize new heuristics from trace history
    - Run meta-meta checks
    - Auto-save genome
    - Adjust exploration rate based on recent performance

    The tick is the agent's "inner monologue" — reflection
    without external stimulus.
    """

    def __init__(
        self,
        min_interval_s: float = 60.0,
        trace_synthesizer: TraceSynthesizer | None = None,
        meta_meta_controller: MetaMetaController | None = None,
    ) -> None:
        self._min_interval = min_interval_s
        self._last_tick: float = 0.0
        self._tick_count: int = 0
        self._synthesizer = trace_synthesizer or TraceSynthesizer()
        self._meta_meta = meta_meta_controller or MetaMetaController()

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def meta_meta(self) -> MetaMetaController:
        return self._meta_meta

    def should_tick(self) -> bool:
        """Check if enough time has elapsed for a diagnostic tick."""
        return (time.monotonic() - self._last_tick) >= self._min_interval

    def execute(
        self,
        strategy: SearchStrategy,
        object_level: ObjectLevel,
        meta_level: MetaLevel,
    ) -> dict[str, Any]:
        """Run the autonomous diagnostic cycle.

        Returns a report of what was done.
        """
        self._last_tick = time.monotonic()
        self._tick_count += 1
        report: dict[str, Any] = {"tick": self._tick_count, "actions": []}

        # 1. Prune dead heuristics
        pruned = self._auto_prune(strategy)
        if pruned:
            report["actions"].append(f"pruned {len(pruned)} dead heuristics: {pruned}")

        # 2. Synthesize new heuristics from traces
        traces = object_level.trace_archive
        new_heuristics = self._synthesizer.synthesize(
            traces,
            strategy.genome.heuristics,
        )
        for h in new_heuristics:
            strategy.mutate_inject(h, reason=f"trace synthesis (tick #{self._tick_count})")
            report["actions"].append(f"synthesized heuristic: {h.name}")

        # 3. Meta-meta self-correction
        diagnoses = self._meta_meta.check_and_correct(meta_level, strategy)
        for d in diagnoses:
            report["actions"].append(f"meta-meta [{d.pattern}]: {d.action_taken}")

        # 4. Exploration rate decay (cool down over time)
        self._cool_exploration(strategy)

        logger.info(
            "AutonomousTick #%d: %d actions",
            self._tick_count,
            len(report["actions"]),
        )
        return report

    def _auto_prune(self, strategy: SearchStrategy) -> list[str]:
        """Prune heuristics with very low fitness and many activations."""
        pruned: list[str] = []
        to_prune = [
            h
            for h in strategy.genome.heuristics
            if h.activation_count > 10 and h.fitness < 0.35 and h.weight < 0.15
        ]
        for h in to_prune:
            strategy.mutate_prune(
                h.name,
                reason=f"auto-prune: fitness={h.fitness:.3f}, activations={h.activation_count}",
            )
            pruned.append(h.name)
        return pruned

    def _cool_exploration(self, strategy: SearchStrategy) -> None:
        """Gradually cool exploration rate toward equilibrium.

        Like simulated annealing: exploration is high early,
        decays toward a baseline as the strategy matures.
        """
        genome = strategy.genome
        generation = genome.generation
        # Target exploration decreases with maturity
        target = max(0.15, 0.5 - (generation * 0.01))
        current = genome.exploration_rate

        if abs(current - target) > 0.05:
            # Move 10% toward target
            new_rate = current + (target - current) * 0.1
            strategy.mutate_exploration_rate(
                new_rate,
                reason=f"cooling (gen={generation}, target={target:.2f})",
            )
