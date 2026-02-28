"""CORTEX Policy Engine — Data Models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ActionItem:
    """A scored, prioritized action derived from CORTEX memory.

    Attributes:
        fact_id: Source fact ID (None for synthetic actions).
        project: Project this action belongs to.
        action_type: Category — resolve_ghost | apply_bridge | fix_error |
                     review_decision | absorb_knowledge.
        description: Human-readable action description.
        value: Final Bellman value score (0.0–1.0, clamped).
        urgency: Time-discounted urgency component.
        impact: Estimated impact (blocking multiplier applied).
        source_type: Original fact_type (ghost, error, bridge, decision, knowledge).
        metadata: Extra context (cross-project deps, tags, etc.).
    """

    fact_id: int | None
    project: str
    action_type: str
    description: str
    value: float
    urgency: float
    impact: float
    source_type: str
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"ActionItem(v={self.value:.3f} "
            f"[{self.action_type}] {self.description[:60]})"
        )


# ── Reward Mapping ──────────────────────────────────────────────────
# Base reward per fact_type.  Higher = more actionable.
# Ghost and error are high because they represent incomplete/broken state.
# Bridge is medium — proven pattern transfer opportunity.
# Decision is low — already resolved.
# Knowledge is lowest — informational, no action needed.

REWARD_MAP: dict[str, float] = {
    "ghost": 0.70,
    "error": 0.90,
    "bridge": 0.50,
    "decision": 0.30,
    "knowledge": 0.10,
}

# Action type mapping from fact_type
ACTION_TYPE_MAP: dict[str, str] = {
    "ghost": "resolve_ghost",
    "error": "fix_error",
    "bridge": "apply_bridge",
    "decision": "review_decision",
    "knowledge": "absorb_knowledge",
}


@dataclass(slots=True)
class PolicyConfig:
    """Tunable parameters for the Bellman value function.

    Attributes:
        gamma: Discount factor (0–1). Higher = future value matters more.
        blocking_multiplier: Score multiplier for items that block other work.
        cross_project_bonus: Additive bonus for cross-project bridges/ghosts.
        error_recency_weight: Multiplier for recently-created errors.
        ghost_age_decay: Per-day multiplicative decay for ghost urgency.
        max_actions: Maximum number of actions to return.
        recency_window_hours: Errors younger than this get the recency bonus.
    """

    gamma: float = 0.90
    blocking_multiplier: float = 3.0
    cross_project_bonus: float = 1.5
    error_recency_weight: float = 2.0
    ghost_age_decay: float = 0.95
    max_actions: int = 20
    recency_window_hours: float = 24.0
