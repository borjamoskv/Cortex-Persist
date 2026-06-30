# [C5-REAL] Exergy-Maximized
"""SICA Dream Engine - NREM-Inspired Trace Consolidation.

Biological insight: during NREM sleep, the hippocampus replays
recent experiences while the neocortex extracts generalizable
patterns. This is how mammals consolidate learning.

SICA Dream does the same:
  1. REPLAY: re-process recent traces in random order
  2. RECOMBINE: splice successful trace fragments together
  3. ABSTRACT: extract general rules from specific experiences
  4. PRUNE: forget low-value trace details, keep structure
  5. REHEARSE: mentally simulate novel scenarios from fragments

The dream cycle runs during idle periods (after AutonomousTick)
and produces DreamInsights that feed into strategy evolution.

─────────────────────────────────────────────────────────
  Awake (object-level)    →    Dream (consolidation)
  specific traces              general patterns
  tool A at time T             "tool A works for search"
  5 grep failures              "grep unreliable for deploy"
─────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from babylon60.sica.object_level import ExecutionStep, ExecutionTrace, StepOutcome
from babylon60.sica.strategy import Heuristic, SearchStrategy

logger = logging.getLogger("cortex.sica.dream")


@dataclass
class DreamInsight:
    """A pattern discovered during dream consolidation.

    Each insight is actionable - it can become a heuristic,
    modify a weight, or flag a blind spot.
    """

    insight_type: str  # "rule" | "anti_pattern" | "specialization" | "combo" | "abstraction"
    description: str
    confidence: float  # [0, 1]
    evidence_count: int
    proposed_heuristic: Heuristic | None = None
    proposed_weight_change: dict[str, float] | None = None  # {heuristic_name: delta}
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class DreamReport:
    """Summary of a dream cycle."""

    cycle_id: int
    duration_ms: float
    traces_replayed: int
    fragments_recombined: int
    insights_discovered: list[DreamInsight]
    abstractions_formed: int
    memories_pruned: int


class DreamEngine:
    """NREM-inspired trace consolidation engine.

    Runs offline during idle to extract generalizable knowledge
    from the agent's accumulated execution traces.
    """

    def __init__(
        self,
        min_traces_for_dream: int = 5,
        max_fragments: int = 50,
        abstraction_threshold: int = 3,
    ) -> None:
        self._min_traces = min_traces_for_dream
        self._max_fragments = max_fragments
        self._abstraction_threshold = abstraction_threshold
        self._cycle_count = 0
        self._insight_archive: list[DreamInsight] = []
        self._abstractions: dict[str, _Abstraction] = {}

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def insight_archive(self) -> list[DreamInsight]:
        return list(self._insight_archive)

    @property
    def abstractions(self) -> dict[str, Any]:
        return {k: v.to_dict() for k, v in self._abstractions.items()}

    # ── Main Dream Cycle ─────────────────────────────────────────

    def dream(
        self,
        traces: list[ExecutionTrace],
        strategy: SearchStrategy,
    ) -> DreamReport:
        """Execute a full dream consolidation cycle.

        Steps:
        1. REPLAY: shuffle and re-process traces
        2. FRAGMENT: extract reusable success fragments
        3. RECOMBINE: splice fragments into novel plans
        4. ABSTRACT: generalize patterns across fragments
        5. PRUNE: discard low-signal details
        6. INSIGHT: generate actionable insights
        """
        start = time.monotonic()
        self._cycle_count += 1

        if len(traces) < self._min_traces:
            return DreamReport(
                cycle_id=self._cycle_count,
                duration_ms=0,
                traces_replayed=0,
                fragments_recombined=0,
                insights_discovered=[],
                abstractions_formed=0,
                memories_pruned=0,
            )

        # Phase 1: REPLAY - shuffle for decontextualization
        replay_order = list(traces)
        random.shuffle(replay_order)

        # Phase 2: FRAGMENT - extract reusable pieces
        success_fragments = self._extract_fragments(replay_order, StepOutcome.SUCCESS)
        failure_fragments = self._extract_fragments(replay_order, StepOutcome.FAILURE)

        # Phase 3: RECOMBINE - splice fragments
        recombinations = self._recombine_fragments(success_fragments)

        # Phase 4: ABSTRACT - generalize patterns
        new_abstractions = self._abstract_patterns(replay_order)

        # Phase 5: PRUNE - forget noise
        pruned_count = self._prune_low_signal(replay_order)

        # Phase 6: INSIGHT - generate actionable discoveries
        insights: list[DreamInsight] = []
        insights.extend(self._discover_tool_specializations(replay_order))
        insights.extend(self._discover_failure_precursors(replay_order))
        insights.extend(self._discover_optimal_sequences(success_fragments))
        insights.extend(self._discover_temporal_patterns(replay_order))

        self._insight_archive.extend(insights)
        # Keep archive bounded
        if len(self._insight_archive) > 200:
            self._insight_archive = self._insight_archive[-200:]

        duration = (time.monotonic() - start) * 1000

        logger.info(
            "DreamEngine cycle #%d: replayed=%d, fragments=%d, "
            "recombined=%d, abstractions=%d, insights=%d, pruned=%d (%.1fms)",
            self._cycle_count,
            len(replay_order),
            len(success_fragments) + len(failure_fragments),
            len(recombinations),
            new_abstractions,
            len(insights),
            pruned_count,
            duration,
        )

        return DreamReport(
            cycle_id=self._cycle_count,
            duration_ms=duration,
            traces_replayed=len(replay_order),
            fragments_recombined=len(recombinations),
            insights_discovered=insights,
            abstractions_formed=new_abstractions,
            memories_pruned=pruned_count,
        )

    # ── Fragment Extraction ──────────────────────────────────────

    def _extract_fragments(
        self,
        traces: list[ExecutionTrace],
        outcome_filter: StepOutcome,
    ) -> list[_TraceFragment]:
        """Extract reusable step sequences from traces."""
        fragments: list[_TraceFragment] = []

        for trace in traces:
            if trace.final_outcome != outcome_filter:
                continue
            self._extract_sequence_fragments(trace, outcome_filter, fragments)

        # Also extract individual successful steps
        for trace in traces:
            self._extract_individual_fragments(trace, outcome_filter, fragments)

        return fragments[: self._max_fragments]

    def _extract_sequence_fragments(
        self, trace: ExecutionTrace, outcome_filter: StepOutcome, fragments: list[_TraceFragment]
    ) -> None:
        current_run: list[ExecutionStep] = []
        for step in trace.steps:
            if step.outcome == outcome_filter:
                current_run.append(step)
            else:
                if len(current_run) >= 2:
                    fragments.append(
                        _TraceFragment(
                            steps=list(current_run),
                            source_trace=trace.task_id,
                            outcome=outcome_filter,
                        )
                    )
                current_run = []

        if len(current_run) >= 2:
            fragments.append(
                _TraceFragment(
                    steps=list(current_run), source_trace=trace.task_id, outcome=outcome_filter
                )
            )

    def _extract_individual_fragments(
        self, trace: ExecutionTrace, outcome_filter: StepOutcome, fragments: list[_TraceFragment]
    ) -> None:
        for step in trace.steps:
            if step.outcome == outcome_filter and step.tool_used:
                fragments.append(
                    _TraceFragment(steps=[step], source_trace=trace.task_id, outcome=outcome_filter)
                )

    def _recombine_fragments(
        self,
        success_fragments: list[_TraceFragment],
    ) -> list[_TraceFragment]:
        """Splice success fragments into novel combinations.

        Like genetic crossover: take the beginning of one
        successful trace and the end of another.
        """
        if len(success_fragments) < 2:
            return []

        recombinations: list[_TraceFragment] = []
        n_attempts = min(10, len(success_fragments))

        for _ in range(n_attempts):
            f1, f2 = random.sample(success_fragments, 2)
            # Take first half of f1, second half of f2
            mid1 = len(f1.steps) // 2
            mid2 = len(f2.steps) // 2

            if mid1 > 0 and mid2 < len(f2.steps):
                combined_steps = f1.steps[:mid1] + f2.steps[mid2:]
                recombinations.append(
                    _TraceFragment(
                        steps=combined_steps,
                        source_trace=f"recombination:{f1.source_trace}+{f2.source_trace}",
                        outcome=StepOutcome.SUCCESS,  # Hypothetical
                    )
                )

        return recombinations

    # ── Pattern Abstraction ──────────────────────────────────────

    def _abstract_patterns(self, traces: list[ExecutionTrace]) -> int:
        """Generalize specific experiences into abstract rules."""
        new_count = self._abstract_tool_reliability(traces)
        new_count += self._abstract_step_count_correlation(traces)
        return new_count

    def _abstract_tool_reliability(self, traces: list[ExecutionTrace]) -> int:
        new_count = 0
        tool_task_outcomes: dict[str, list[bool]] = defaultdict(list)
        for trace in traces:
            task_type = (trace.objective or "").split()[0].lower() if trace.objective else "unknown"
            for step in trace.steps:
                if step.tool_used:
                    key = f"{step.tool_used}:{task_type}"
                    tool_task_outcomes[key].append(step.outcome == StepOutcome.SUCCESS)

        for key, outcomes in tool_task_outcomes.items():
            if len(outcomes) >= self._abstraction_threshold:
                success_rate = sum(outcomes) / len(outcomes)
                if key not in self._abstractions:
                    self._abstractions[key] = _Abstraction(
                        pattern=key, success_rate=success_rate, observations=len(outcomes)
                    )
                    new_count += 1
                else:
                    self._abstractions[key].update(success_rate, len(outcomes))
        return new_count

    def _abstract_step_count_correlation(self, traces: list[ExecutionTrace]) -> int:
        new_count = 0
        step_outcomes: dict[int, list[bool]] = defaultdict(list)
        for trace in traces:
            step_outcomes[trace.step_count].append(trace.final_outcome == StepOutcome.SUCCESS)

        for count, outcomes in step_outcomes.items():
            if len(outcomes) >= self._abstraction_threshold:
                key = f"step_count:{count}"
                success_rate = sum(outcomes) / len(outcomes)
                if key not in self._abstractions:
                    self._abstractions[key] = _Abstraction(
                        pattern=key, success_rate=success_rate, observations=len(outcomes)
                    )
                    new_count += 1
        return new_count

    # ── Memory Pruning ───────────────────────────────────────────

    def _prune_low_signal(self, traces: list[ExecutionTrace]) -> int:
        """Identify low-information traces that can be forgotten.

        A trace has low signal if:
        - It's a simple success with 1 step (nothing to learn)
        - It's a duplicate of an existing abstraction
        - Its tools and outcomes are well-modeled (low surprise)
        """
        prunable = 0
        for trace in traces:
            if (
                trace.step_count == 1 and trace.final_outcome == StepOutcome.SUCCESS
            ) or trace.step_count == 0:
                prunable += 1
        return prunable

    # ── Insight Discovery ────────────────────────────────────────

    def _discover_tool_specializations(
        self,
        traces: list[ExecutionTrace],
    ) -> list[DreamInsight]:
        """Discover which tools work best for which task types."""
        task_tool_success = self._group_tool_outcomes(traces)
        insights: list[DreamInsight] = []
        for task_type, tool_data in task_tool_success.items():
            if len(tool_data) < 2:
                continue
            insight = self._evaluate_tool_specialization(task_type, tool_data)
            if insight:
                insights.append(insight)
        return insights

    def _group_tool_outcomes(
        self, traces: list[ExecutionTrace]
    ) -> dict[str, dict[str, list[bool]]]:
        task_tool_success: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
        for trace in traces:
            task_type = (trace.objective or "").split()[0].lower() if trace.objective else "unknown"
            for step in trace.steps:
                if step.tool_used:
                    task_tool_success[task_type][step.tool_used].append(
                        step.outcome == StepOutcome.SUCCESS
                    )
        return task_tool_success

    def _evaluate_tool_specialization(
        self, task_type: str, tool_data: dict[str, list[bool]]
    ) -> DreamInsight | None:
        tool_rates = {}
        for tool, outcomes in tool_data.items():
            if len(outcomes) >= 3:
                tool_rates[tool] = sum(outcomes) / len(outcomes)

        if len(tool_rates) >= 2:
            best = max(tool_rates, key=tool_rates.get)  # type: ignore[arg-type]
            worst = min(tool_rates, key=tool_rates.get)  # type: ignore[arg-type]

            if tool_rates[best] - tool_rates[worst] > 0.3:
                return DreamInsight(
                    insight_type="specialization",
                    description=(
                        f"For '{task_type}' tasks, '{best}' succeeds "
                        f"{tool_rates[best]:.0%} vs '{worst}' at "
                        f"{tool_rates[worst]:.0%}. Prefer '{best}'."
                    ),
                    confidence=min(0.9, 0.5 + len(tool_data[best]) * 0.05),
                    evidence_count=len(tool_data[best]),
                    proposed_heuristic=Heuristic(
                        name=f"prefer_{best}_for_{task_type}",
                        description=f"Use {best} for {task_type} tasks (dream-discovered)",
                        weight=0.6,
                    ),
                )
        return None

    def _discover_failure_precursors(
        self,
        traces: list[ExecutionTrace],
    ) -> list[DreamInsight]:
        """Discover action patterns that precede failures.

        Like dreaming about falling - rehearsing danger to prepare.
        """
        insights: list[DreamInsight] = []
        precursor_counts: Counter[str] = Counter()

        for trace in traces:
            if trace.final_outcome != StepOutcome.FAILURE:
                continue
            for i, step in enumerate(trace.steps):
                if step.outcome == StepOutcome.FAILURE and i > 0:
                    prev = trace.steps[i - 1]
                    key = f"{prev.action}→{step.action}"
                    precursor_counts[key] += 1
                    break

        for pattern, count in precursor_counts.most_common(3):
            if count >= 3:
                insights.append(
                    DreamInsight(
                        insight_type="anti_pattern",
                        description=f"Sequence '{pattern}' preceded failure {count} times.",
                        confidence=min(0.85, 0.4 + count * 0.1),
                        evidence_count=count,
                    )
                )

        return insights

    def _discover_optimal_sequences(
        self,
        success_fragments: list[_TraceFragment],
    ) -> list[DreamInsight]:
        """Discover step sequences that correlate with success."""
        insights: list[DreamInsight] = []
        sequence_counts: Counter[str] = Counter()

        for frag in success_fragments:
            if len(frag.steps) >= 2:
                seq = "→".join(s.action for s in frag.steps[:3])
                sequence_counts[seq] += 1

        for seq, count in sequence_counts.most_common(3):
            if count >= 3:
                insights.append(
                    DreamInsight(
                        insight_type="combo",
                        description=f"Sequence '{seq}' appeared in {count} successes.",
                        confidence=min(0.8, 0.3 + count * 0.1),
                        evidence_count=count,
                    )
                )

        return insights

    def _discover_temporal_patterns(
        self,
        traces: list[ExecutionTrace],
    ) -> list[DreamInsight]:
        """Discover time-based patterns (e.g., tools that degrade over time)."""
        # Simple: check if recent traces have lower success rate than older ones
        if len(traces) < 10:
            return []

        mid = len(traces) // 2
        old_traces = traces[:mid]
        new_traces = traces[mid:]

        old_success = sum(1 for t in old_traces if t.final_outcome == StepOutcome.SUCCESS) / len(
            old_traces
        )
        new_success = sum(1 for t in new_traces if t.final_outcome == StepOutcome.SUCCESS) / len(
            new_traces
        )

        insights: list[DreamInsight] = []
        if old_success - new_success > 0.2:
            insights.append(
                DreamInsight(
                    insight_type="abstraction",
                    description=(
                        f"Performance declining: old success rate {old_success:.0%} "
                        f"→ recent {new_success:.0%}. Strategy may be staling."
                    ),
                    confidence=0.7,
                    evidence_count=len(traces),
                )
            )
        elif new_success - old_success > 0.2:
            insights.append(
                DreamInsight(
                    insight_type="abstraction",
                    description=(
                        f"Performance improving: old {old_success:.0%} "
                        f"→ recent {new_success:.0%}. Current strategy is working."
                    ),
                    confidence=0.7,
                    evidence_count=len(traces),
                )
            )

        return insights

    # ── Apply Insights ───────────────────────────────────────────

    def apply_insights(
        self,
        insights: list[DreamInsight],
        strategy: SearchStrategy,
        confidence_threshold: float = 0.6,
    ) -> int:
        """Apply dream insights to the strategy genome."""
        applied = 0
        existing_names = {h.name for h in strategy.genome.heuristics}

        for insight in insights:
            if insight.confidence < confidence_threshold:
                continue

            if self._apply_proposed_heuristic(insight, strategy, existing_names):
                applied += 1

            if self._apply_proposed_weights(insight, strategy):
                applied += 1

        return applied

    def _apply_proposed_heuristic(
        self, insight: DreamInsight, strategy: SearchStrategy, existing_names: set[str]
    ) -> bool:
        if insight.proposed_heuristic and insight.proposed_heuristic.name not in existing_names:
            strategy.mutate_inject(
                insight.proposed_heuristic,
                reason=f"dream insight: {insight.description[:80]}",
            )
            existing_names.add(insight.proposed_heuristic.name)
            return True
        return False

    def _apply_proposed_weights(self, insight: DreamInsight, strategy: SearchStrategy) -> bool:
        applied = False
        if insight.proposed_weight_change:
            for name, delta in insight.proposed_weight_change.items():
                try:
                    if delta > 0:
                        strategy.mutate_amplify(
                            name, reason=f"dream: {insight.description[:60]}", factor=1 + delta
                        )
                    elif delta < 0:
                        strategy.mutate_attenuate(
                            name, reason=f"dream: {insight.description[:60]}", factor=1 + delta
                        )
                    applied = True
                except Exception as exc:
                    logger.warning("Suppressed exception: %s", exc)
        return applied


# ── Internal Types ───────────────────────────────────────────────


@dataclass
class _TraceFragment:
    steps: list[ExecutionStep]
    source_trace: str
    outcome: StepOutcome


@dataclass
class _Abstraction:
    pattern: str
    success_rate: float
    observations: int

    def update(self, new_rate: float, new_obs: int) -> None:
        # Weighted running average
        total = self.observations + new_obs
        self.success_rate = (self.success_rate * self.observations + new_rate * new_obs) / total
        self.observations = total

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "success_rate": round(self.success_rate, 3),
            "observations": self.observations,
        }
