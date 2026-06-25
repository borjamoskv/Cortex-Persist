# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging
from collections import Counter

from legacy_research.sica.object_level import ExecutionTrace, StepOutcome
from legacy_research.sica.strategy import Heuristic

logger = logging.getLogger("cortex.sica.autonomy.trace")


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
