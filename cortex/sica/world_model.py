# [C5-REAL] Exergy-Maximized
"""SICA World Model - Causal Prediction & Counterfactual Reasoning.

The agent currently REACTS to failures. A world model lets it
PREDICT outcomes before executing, and reason about
WHAT WOULD HAVE HAPPENED with different choices.

Architecture:
  ┌─────────────────────────────────────────────┐
  │           WORLD MODEL                        │
  │                                              │
  │  ToolOutcomeModel: P(success|tool,context)   │
  │  ContextEncoder: task→features               │
  │  CausalGraph: tool→outcome→consequence       │
  │  Counterfactual: "what if I had chosen X?"   │
  └─────────────────────────────────────────────┘

Key insight: the agent builds a Bayesian model of
tool→outcome probabilities conditioned on context,
then uses it to PLAN before acting.
"""

from __future__ import annotations

import logging
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from cortex.sica.object_level import ExecutionStep, ExecutionTrace, StepOutcome

logger = logging.getLogger("cortex.sica.world_model")


# ═══════════════════════════════════════════════════════════════════
# BAYESIAN TOOL-OUTCOME MODEL
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ToolBelief:
    """Bayesian belief about a tool's success probability.

    Uses Beta distribution (conjugate prior for Bernoulli):
      alpha = prior successes + observed successes
      beta  = prior failures + observed failures
      E[p]  = alpha / (alpha + beta)

    This gives us principled uncertainty quantification -
    a tool used once successfully has high uncertainty,
    a tool used 100 times successfully has low uncertainty.
    """

    tool_name: str
    alpha: float = 1.0  # Prior: 1 success (optimistic prior)
    beta: float = 1.0  # Prior: 1 failure
    last_updated: float = field(default_factory=time.monotonic)

    @property
    def expected_success(self) -> float:
        """E[p] = α / (α + β)."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def uncertainty(self) -> float:
        """Variance of Beta distribution = αβ / ((α+β)²(α+β+1))."""
        total = self.alpha + self.beta
        return (self.alpha * self.beta) / (total * total * (total + 1))

    @property
    def confidence(self) -> float:
        """Confidence = 1 - normalized uncertainty. [0,1]."""
        # Max uncertainty is at α=β=1 → 0.25/3 ≈ 0.083
        max_var = 0.083
        return 1.0 - min(1.0, self.uncertainty / max_var)

    @property
    def observations(self) -> int:
        """Total observations (excluding priors)."""
        return int(self.alpha + self.beta - 2)  # Subtract priors

    def observe_success(self) -> None:
        self.alpha += 1
        self.last_updated = time.monotonic()

    def observe_failure(self) -> None:
        self.beta += 1
        self.last_updated = time.monotonic()

    def ucb_score(self, total_selections: int, exploration_c: float = 1.414) -> float:
        """Upper Confidence Bound for intelligent exploration.

        UCB1 = E[p] + c * sqrt(ln(N) / n)
        Balances exploitation (high E[p]) with exploration (high uncertainty).
        """
        n = self.observations + 1  # Avoid div by zero
        return self.expected_success + exploration_c * math.sqrt(
            math.log(max(1, total_selections)) / n
        )


@dataclass
class ContextualBelief:
    """Tool belief conditioned on context features.

    Maintains separate beliefs per (tool, context_key) pair,
    enabling context-dependent predictions:
      P(success | tool=grep, task_type=search) ≠ P(success | tool=grep, task_type=deploy)
    """

    tool_name: str
    context_key: str  # e.g., "task_type:search"
    belief: ToolBelief = field(default_factory=lambda: ToolBelief(tool_name=""))

    def __post_init__(self) -> None:
        self.belief.tool_name = self.tool_name


class WorldModel:
    """Predictive model of the agent's environment.

    Learns from execution traces to build a Bayesian model of:
    - Which tools succeed in which contexts
    - Action sequences that lead to success/failure
    - Temporal patterns in tool reliability

    Uses Upper Confidence Bounds (UCB) for exploration-exploitation
    in tool selection - theoretically optimal for multi-armed bandits.
    """

    def __init__(self, exploration_c: float = 1.414) -> None:
        self._tool_beliefs: dict[str, ToolBelief] = {}
        self._contextual_beliefs: dict[str, ContextualBelief] = {}
        self._transition_model: dict[str, Counter[str]] = defaultdict(Counter)
        self._total_selections: int = 0
        self._exploration_c = exploration_c

        # Causal chains: action_a → outcome → action_b
        self._causal_chains: list[_CausalChain] = []

    @property
    def tool_beliefs(self) -> dict[str, ToolBelief]:
        return dict(self._tool_beliefs)

    # ── Learning from Traces ─────────────────────────────────────

    def learn(self, trace: ExecutionTrace) -> None:
        """Update the world model from a completed execution trace.

        Extracts:
        1. Tool → outcome observations (Bayesian update)
        2. Action transitions (Markov chain)
        3. Causal chains (what caused what)
        """
        context_key = self._encode_context(trace)

        for step in trace.steps:
            if step.tool_used:
                self._update_tool_belief(step.tool_used, step.outcome)
                self._update_contextual_belief(step.tool_used, context_key, step.outcome)
                self._total_selections += 1

        # Learn action transitions
        for i in range(len(trace.steps) - 1):
            current = trace.steps[i].action
            next_action = trace.steps[i + 1].action
            self._transition_model[current][next_action] += 1

        # Extract causal chains
        chain = self._extract_causal_chain(trace)
        if chain:
            self._causal_chains.append(chain)
            # Keep only recent chains
            if len(self._causal_chains) > 500:
                self._causal_chains = self._causal_chains[-500:]

    def learn_batch(self, traces: list[ExecutionTrace]) -> None:
        """Learn from multiple traces."""
        for trace in traces:
            self.learn(trace)

    # ── Prediction ───────────────────────────────────────────────

    def predict_tool_success(
        self,
        tool_name: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[float, float]:
        """Predict P(success) for a tool, with uncertainty.

        Returns (expected_success, uncertainty).
        If context is provided, uses contextual belief.
        """
        if context:
            context_key = self._context_to_key(context)
            ckey = f"{tool_name}:{context_key}"
            if ckey in self._contextual_beliefs:
                belief = self._contextual_beliefs[ckey].belief
                return belief.expected_success, belief.uncertainty

        if tool_name in self._tool_beliefs:
            belief = self._tool_beliefs[tool_name]
            return belief.expected_success, belief.uncertainty

        return 0.5, 0.083  # Maximum uncertainty prior

    def rank_tools(
        self,
        candidates: list[str],
        context: dict[str, Any] | None = None,
        use_ucb: bool = True,
    ) -> list[tuple[str, float, float]]:
        """Rank tools by predicted success, balancing exploration.

        Returns list of (tool_name, score, uncertainty) sorted by score desc.

        If use_ucb=True, uses Upper Confidence Bound to balance
        exploitation (high success rate) with exploration (uncertain tools).
        """
        scored: list[tuple[str, float, float]] = []

        for tool in candidates:
            p_success, uncertainty = self.predict_tool_success(tool, context)

            if use_ucb and tool in self._tool_beliefs:
                score = self._tool_beliefs[tool].ucb_score(
                    self._total_selections,
                    self._exploration_c,
                )
            else:
                score = p_success

            scored.append((tool, score, uncertainty))

        return sorted(scored, key=lambda x: x[1], reverse=True)

    def predict_next_action(self, current_action: str) -> list[tuple[str, float]]:
        """Predict the most likely next action given current action.

        Uses the learned Markov transition model.
        Returns list of (action, probability) sorted by probability desc.
        """
        if current_action not in self._transition_model:
            return []

        counts = self._transition_model[current_action]
        total = sum(counts.values())
        if total == 0:
            return []

        return sorted(
            [(action, count / total) for action, count in counts.items()],
            key=lambda x: x[1],
            reverse=True,
        )

    # ── Counterfactual Reasoning ─────────────────────────────────

    def counterfactual(
        self,
        trace: ExecutionTrace,
        step_index: int,
        alternative_tool: str,
    ) -> dict[str, Any]:
        """What would have happened if we'd used a different tool?

        Simulates the counterfactual by:
        1. Looking up P(success|alternative_tool, context)
        2. Comparing with actual outcome
        3. Estimating counterfactual trace outcome

        This is NOT causal inference (requires interventional data).
        It's a principled heuristic using our Bayesian beliefs.
        """
        if step_index >= len(trace.steps):
            return {"error": "step_index out of range"}

        actual_step = trace.steps[step_index]
        actual_outcome = actual_step.outcome
        actual_tool = actual_step.tool_used or "unknown"

        # Get beliefs for both tools
        p_actual, u_actual = self.predict_tool_success(actual_tool)
        p_alt, u_alt = self.predict_tool_success(alternative_tool)

        # Estimate counterfactual outcome
        delta = p_alt - p_actual
        cf_would_succeed = p_alt > 0.5

        # Compute regret: how much better/worse would the alternative have been?
        if actual_outcome == StepOutcome.SUCCESS:
            regret = max(0, p_alt - p_actual)  # Opportunity cost
        else:
            regret = max(0, p_alt - p_actual)  # Potential gain

        return {
            "actual_tool": actual_tool,
            "actual_outcome": actual_outcome.value,
            "actual_p_success": round(p_actual, 3),
            "alternative_tool": alternative_tool,
            "alternative_p_success": round(p_alt, 3),
            "alternative_uncertainty": round(u_alt, 4),
            "would_have_succeeded": cf_would_succeed,
            "delta_p": round(delta, 3),
            "regret": round(regret, 3),
            "confidence_in_counterfactual": round(1 - u_alt / 0.083, 3),
        }

    def regret_analysis(self, trace: ExecutionTrace) -> list[dict[str, Any]]:
        """Analyze regret across all steps in a trace.

        For each failed step that used a tool, compute the
        counterfactual for every other known tool.

        Returns opportunities where a different tool choice
        would likely have succeeded.
        """
        opportunities: list[dict[str, Any]] = []

        known_tools = list(self._tool_beliefs.keys())
        if not known_tools:
            return opportunities

        for i, step in enumerate(trace.steps):
            if step.outcome != StepOutcome.FAILURE or not step.tool_used:
                continue

            for alt_tool in known_tools:
                if alt_tool == step.tool_used:
                    continue
                cf = self.counterfactual(trace, i, alt_tool)
                if cf.get("would_have_succeeded"):
                    opportunities.append(cf)

        return sorted(opportunities, key=lambda x: x["regret"], reverse=True)

    # ── Surprise Detection ───────────────────────────────────────

    def surprise(self, step: ExecutionStep) -> float:
        """How surprising is this outcome given our model?

        High surprise = the model predicted differently from reality.
        This drives learning: surprising outcomes update beliefs more.

        Returns surprise ∈ [0, 1] where 1 = maximally surprising.
        """
        if not step.tool_used:
            return 0.0

        p_success, _ = self.predict_tool_success(step.tool_used)

        if step.outcome == StepOutcome.SUCCESS:
            # Surprise = probability we assigned to failure
            return 1.0 - p_success
        if step.outcome == StepOutcome.FAILURE:
            # Surprise = probability we assigned to success
            return p_success
        return 0.0

    # ── Internals ────────────────────────────────────────────────

    def _update_tool_belief(self, tool: str, outcome: StepOutcome) -> None:
        if tool not in self._tool_beliefs:
            self._tool_beliefs[tool] = ToolBelief(tool_name=tool)
        belief = self._tool_beliefs[tool]
        if outcome == StepOutcome.SUCCESS:
            belief.observe_success()
        elif outcome == StepOutcome.FAILURE:
            belief.observe_failure()

    def _update_contextual_belief(
        self,
        tool: str,
        context_key: str,
        outcome: StepOutcome,
    ) -> None:
        ckey = f"{tool}:{context_key}"
        if ckey not in self._contextual_beliefs:
            self._contextual_beliefs[ckey] = ContextualBelief(
                tool_name=tool,
                context_key=context_key,
            )
        belief = self._contextual_beliefs[ckey].belief
        if outcome == StepOutcome.SUCCESS:
            belief.observe_success()
        elif outcome == StepOutcome.FAILURE:
            belief.observe_failure()

    def _encode_context(self, trace: ExecutionTrace) -> str:
        """Extract context features from a trace."""
        objective = trace.objective or ""
        # Simple context: first word of objective as task type
        task_type = objective.split()[0].lower() if objective else "unknown"
        return f"task_type:{task_type}"

    def _context_to_key(self, context: dict[str, Any]) -> str:
        task_type = context.get("task_type", "unknown")
        return f"task_type:{task_type}"

    def _extract_causal_chain(self, trace: ExecutionTrace) -> _CausalChain | None:
        """Extract the causal chain from a trace."""
        if len(trace.steps) < 2:
            return None

        links = []
        for i in range(len(trace.steps) - 1):
            links.append(
                _CausalLink(
                    action=trace.steps[i].action,
                    outcome=trace.steps[i].outcome,
                    next_action=trace.steps[i + 1].action,
                )
            )

        return _CausalChain(
            trace_id=trace.task_id,
            links=links,
            final_outcome=trace.final_outcome or StepOutcome.FAILURE,
        )

    # ── Introspection ────────────────────────────────────────────

    def introspect(self) -> dict[str, Any]:
        """Full world model state."""
        return {
            "tools_modeled": len(self._tool_beliefs),
            "contextual_beliefs": len(self._contextual_beliefs),
            "total_observations": self._total_selections,
            "causal_chains": len(self._causal_chains),
            "transition_states": len(self._transition_model),
            "tool_rankings": {
                name: {
                    "p_success": round(b.expected_success, 3),
                    "uncertainty": round(b.uncertainty, 4),
                    "confidence": round(b.confidence, 3),
                    "observations": b.observations,
                }
                for name, b in sorted(
                    self._tool_beliefs.items(),
                    key=lambda x: x[1].expected_success,
                    reverse=True,
                )
            },
        }


# ── Internal dataclasses ─────────────────────────────────────────


@dataclass
class _CausalLink:
    action: str
    outcome: StepOutcome
    next_action: str


@dataclass
class _CausalChain:
    trace_id: str
    links: list[_CausalLink]
    final_outcome: StepOutcome
