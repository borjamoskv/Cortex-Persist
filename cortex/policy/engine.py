"""CORTEX Policy Engine — Bellman Value Function.

Converts CORTEX memory into a prioritized action queue using
a Bellman-inspired value function: V(s) = R(s,a) + γ·V(s').

No new DB tables. Operates entirely on existing recall()/search() data.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from cortex.policy.models import (
    ACTION_TYPE_MAP,
    REWARD_MAP,
    ActionItem,
    PolicyConfig,
)

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.engine.models import Fact

logger = logging.getLogger("cortex.policy")

__all__ = ["PolicyEngine"]

# ISO format used by CORTEX timestamps.
_ISO_FMT = "%Y-%m-%dT%H:%M:%S"
_ISO_FMT_FRAC = "%Y-%m-%dT%H:%M:%S.%f"


def _parse_ts(ts: str | None) -> datetime | None:
    """Parse a CORTEX timestamp string to datetime (UTC)."""
    if not ts:
        return None
    ts = ts.strip()
    for fmt in (_ISO_FMT_FRAC, _ISO_FMT):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    # Last resort: truncate to seconds precision
    try:
        return datetime.strptime(ts[:19], _ISO_FMT).replace(tzinfo=timezone.utc)
    except (ValueError, IndexError):
        return None


class PolicyEngine:
    """Bellman-inspired policy engine for CORTEX.

    Consumes facts from CortexEngine, scores each via a value function,
    and returns a ranked action queue.

    The value function:
        V(s) = R(s,a) + γ · V(s')

    Where:
        R(s,a) = immediate reward (urgency × impact)
        V(s')  = estimated future value (downstream unlock potential)
        γ      = discount factor from PolicyConfig
    """

    __slots__ = ("_engine", "_config")

    def __init__(
        self,
        engine: CortexEngine,
        config: PolicyConfig | None = None,
    ) -> None:
        self._engine = engine
        self._config = config or PolicyConfig()

    @property
    def config(self) -> PolicyConfig:
        return self._config

    # ── Public API ──────────────────────────────────────────────────

    async def evaluate(
        self,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> list[ActionItem]:
        """Evaluate all active facts and return a prioritized action queue.

        Args:
            project: Scope to a single project. None = all projects.
            tenant_id: Tenant scope.

        Returns:
            Sorted list of ActionItems (highest value first).
        """
        facts = await self._gather_facts(project, tenant_id)
        if not facts:
            return []

        # Build cross-reference index for future value estimation.
        project_index: dict[str, list[Fact]] = {}
        for f in facts:
            project_index.setdefault(f.project, []).append(f)

        now = datetime.now(timezone.utc)
        actions: list[ActionItem] = []

        for fact in facts:
            action = self._score_fact(fact, project_index, now)
            if action.value > 0.0:
                actions.append(action)

        # Sort descending by value (highest priority first).
        actions.sort(key=lambda a: a.value, reverse=True)

        return actions[: self._config.max_actions]

    # ── Scoring ─────────────────────────────────────────────────────

    def _score_fact(
        self,
        fact: Fact,
        project_index: dict[str, list[Fact]],
        now: datetime,
    ) -> ActionItem:
        """Convert a Fact into a scored ActionItem via Bellman equation."""
        reward = self._compute_reward(fact, now)
        future = self._compute_future_value(fact, project_index)
        value = self._bellman_value(reward, future, self._config.gamma)

        # Clamp to [0, 1].
        value = max(0.0, min(1.0, value))

        fact_type = (fact.fact_type or "knowledge").lower()
        action_type = ACTION_TYPE_MAP.get(fact_type, "absorb_knowledge")

        return ActionItem(
            fact_id=fact.id,
            project=fact.project,
            action_type=action_type,
            description=self._describe_action(fact, action_type),
            value=value,
            urgency=reward,
            impact=future,
            source_type=fact_type,
            metadata={
                "tags": fact.tags,
                "confidence": fact.confidence,
                "consensus_score": fact.consensus_score,
                "created_at": fact.created_at,
            },
        )

    @staticmethod
    def _bellman_value(reward: float, future_value: float, gamma: float) -> float:
        """V(s) = R(s,a) + γ · V(s')."""
        return reward + gamma * future_value

    def _compute_reward(self, fact: Fact, now: datetime) -> float:
        """Map fact to immediate reward (urgency × impact modifiers)."""
        fact_type = (fact.fact_type or "knowledge").lower()
        base = REWARD_MAP.get(fact_type, 0.1)

        # Time discount: older facts decay.
        created = _parse_ts(fact.created_at)
        if created:
            age_days = max(0.0, (now - created).total_seconds() / 86400)
            if fact_type == "ghost":
                # Ghosts decay per-day.
                time_factor = self._config.ghost_age_decay ** age_days
            elif fact_type == "error":
                # Recent errors get a recency bonus.
                age_hours = age_days * 24
                if age_hours < self._config.recency_window_hours:
                    time_factor = self._config.error_recency_weight
                else:
                    time_factor = max(0.3, 1.0 - (age_days / 30))
            else:
                # Generic slow decay.
                time_factor = max(0.2, 1.0 - (age_days / 90))
        else:
            time_factor = 0.5  # Unknown age → conservative.

        # Confidence modifier: low confidence → higher urgency to verify.
        conf = (fact.confidence or "").lower()
        conf_multiplier = {
            "c1": 1.3,  # Hypothesis needs validation.
            "c2": 1.2,  # Speculative.
            "c3": 1.0,  # Inferred — neutral.
            "c4": 0.9,  # Probable — slightly less urgent.
            "c5": 0.8,  # Confirmed — least urgent.
        }.get(conf, 1.0)

        # Consensus: low consensus → needs attention.
        consensus_mod = 1.0
        if fact.consensus_score < 0.5:
            consensus_mod = 1.3

        return min(1.0, base * time_factor * conf_multiplier * consensus_mod)

    def _compute_future_value(
        self,
        fact: Fact,
        project_index: dict[str, list[Fact]],
    ) -> float:
        """Estimate downstream value of resolving this fact.

        Cross-project references and blocking ghosts increase future value.
        """
        future = 0.0
        fact_type = (fact.fact_type or "knowledge").lower()
        content_lower = (fact.content or "").lower()

        # Cross-project detection: if fact content mentions another project.
        other_projects = set(project_index.keys()) - {fact.project}
        for other in other_projects:
            if other.lower() in content_lower:
                future += self._config.cross_project_bonus
                break  # Only count once.

        # Blocking multiplier: ghosts and errors that reference
        # architectural/critical keywords are likely blocking.
        blocking_keywords = frozenset({
            "blocking", "blocked", "critical", "urgent",
            "deploy", "ship", "production", "release",
            "security", "vulnerability", "crash", "broken",
        })
        if fact_type in ("ghost", "error"):
            if any(kw in content_lower for kw in blocking_keywords):
                future += self._config.blocking_multiplier

        # Bridge downstream: bridges unlock pattern reuse across projects.
        if fact_type == "bridge":
            # Count how many projects could benefit.
            mentioned = sum(
                1 for p in other_projects if p.lower() in content_lower
            )
            future += mentioned * 0.3

        # Normalize to [0, 1] range.
        # Use sigmoid-like compression for high values.
        if future > 0:
            future = 1.0 - math.exp(-future / 3.0)

        return future

    # ── Helpers ──────────────────────────────────────────────────────

    async def _gather_facts(
        self,
        project: str | None,
        tenant_id: str,
    ) -> list[Fact]:
        """Gather active facts from CORTEX engine."""
        if project:
            return await self._engine.recall(project, tenant_id=tenant_id)

        # All projects: get stats then recall each.
        try:
            stats = await self._engine.stats()
        except Exception:
            logger.warning("Failed to get stats, falling back to empty")
            return []

        all_facts: list[Fact] = []
        projects = stats.get("projects", {})
        for proj_name in projects:
            try:
                facts = await self._engine.recall(proj_name, tenant_id=tenant_id)
                all_facts.extend(facts)
            except Exception:
                logger.warning("Failed to recall project %s", proj_name)
        return all_facts

    @staticmethod
    def _describe_action(fact: Fact, action_type: str) -> str:
        """Generate a human-readable action description."""
        content = (fact.content or "")[:120]
        prefix = {
            "resolve_ghost": "🔮 Resolve ghost",
            "fix_error": "🔴 Fix error",
            "apply_bridge": "🌉 Apply bridge pattern",
            "review_decision": "📋 Review decision",
            "absorb_knowledge": "📚 Absorb knowledge",
        }.get(action_type, "📌 Process")

        return f"{prefix} [{fact.project}]: {content}"
