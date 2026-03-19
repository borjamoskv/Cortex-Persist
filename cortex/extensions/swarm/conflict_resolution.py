"""CORTEX v8.0 — Conflict Resolution Protocol (LEGION-Ω).

4-tier escalation: Triangulation → Weighted Vote → Architect → Heuristic Deadlock.
Axioms: Ω₃ (Byzantine), Ω₂ (Entropic Asymmetry), Ω₅ (Antifragile).
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cortex.extensions.llm._models import ReasoningMode
from cortex.extensions.swarm.telemetry_gate import sovereign_quality_gate_async
from cortex.utils.result import Ok, Result

logger = logging.getLogger("cortex.extensions.swarm.conflict_resolution")


class ConflictType(str, Enum):
    """Classification of conflict nature."""

    FACTUAL = "factual"  # Verifiable, e.g. version numbers
    STRATEGIC = "strategic"  # Trade-off dependent, e.g. mono vs micro
    RESOURCE = "resource"  # Scheduling contention
    PRIORITY = "priority"  # Ordering disputes


class ResolutionMethod(str, Enum):
    """How the conflict was ultimately resolved."""

    TRIANGULATION = "triangulation"
    WEIGHTED_VOTE = "weighted-vote"
    ARCHITECT_ARBITRATION = "architect-arbitration"
    DEADLOCK_HEURISTIC = "deadlock-heuristic"
    HUMAN_ESCALATION = "human-escalation"


@dataclass(frozen=True)
class ConflictOption:
    """A single proposed solution in a conflict."""

    id: str
    description: str
    proposer_id: str
    confidence: float = 0.5  # Self-reported by agent [0, 1]
    reversibility: float = 0.5  # How easily this can be undone [0, 1]
    estimated_cost: float = 0.0  # Abstract cost units


@dataclass()
class AgentProfile:
    """Lightweight agent profile for vote weight calculation."""

    agent_id: str
    specialty: str = "general"
    success_rate: float = 0.5  # Historical accuracy [0, 1]
    confidence: float = 0.5  # Current self-assessed confidence [0, 1]
    recency_score: float = 0.0  # How recently active in this domain [0, 1]


@dataclass(frozen=True)
class WeightedVote:
    """A vote cast with computed weight."""

    agent_id: str
    option_id: str
    weight: float
    # Diagnostic breakdown
    domain_component: float
    track_component: float
    confidence_component: float
    recency_component: float


@dataclass()
class ConflictResolution:
    """Full resolution record — persisted as a knowledge item."""

    conflict_id: str
    timestamp: float
    conflict_type: ConflictType
    participants: list[str]
    options: list[ConflictOption]
    resolution: ResolutionResult
    votes: list[WeightedVote] = field(default_factory=list)
    debate_rounds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflictId": self.conflict_id,
            "timestamp": self.timestamp,
            "type": self.conflict_type.value,
            "participants": self.participants,
            "options": [
                {"id": o.id, "description": o.description, "proposer": o.proposer_id}
                for o in self.options
            ],
            "resolution": self.resolution.to_dict(),
            "debateRounds": self.debate_rounds,
        }


@dataclass(frozen=True)
class ResolutionResult:
    """Outcome of a conflict resolution round."""

    winner_id: str
    method: ResolutionMethod
    consensus_level: float  # 0-1, fraction agreeing
    reasoning: str
    total_weight_for: float = 0.0
    total_weight_against: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "winner": self.winner_id,
            "method": self.method.value,
            "consensusLevel": round(self.consensus_level, 3),
            "reasoning": self.reasoning,
            "weightFor": round(self.total_weight_for, 4),
            "weightAgainst": round(self.total_weight_against, 4),
        }


# Weight distribution constants (sum = 1.0)
_W_DOMAIN: float = 0.40
_W_TRACK: float = 0.30
_W_CONFIDENCE: float = 0.20
_W_RECENCY: float = 0.10


def calculate_vote_weight(agent: AgentProfile, conflict_domain: str) -> WeightedVote | None:
    """Compute reputation-weighted vote score for an agent."""
    domain_match = 1.0 if agent.specialty.lower() == conflict_domain.lower() else 0.3

    d = domain_match * _W_DOMAIN
    t = agent.success_rate * _W_TRACK
    c = agent.confidence * _W_CONFIDENCE
    r = agent.recency_score * _W_RECENCY

    weight = round(d + t + c + r, 4)

    return WeightedVote(
        agent_id=agent.agent_id,
        option_id="",  # Set by caller
        weight=weight,
        domain_component=round(d, 4),
        track_component=round(t, 4),
        confidence_component=round(c, 4),
        recency_component=round(r, 4),
    )


def architect_evaluator(inputs: dict[str, Any], output: Any) -> float:
    """Evaluate Architect Arbitration for valid options and confidence."""
    if not isinstance(output, dict):
        return 0.0
    
    winner_id = output.get("winner_id")
    if not isinstance(winner_id, str) or not winner_id:
        return 0.0
        
    valid_ids = inputs.get("valid_ids", set())
    if valid_ids and winner_id not in valid_ids:
        return 0.0
        
    reasoning = output.get("reasoning", "")
    if not isinstance(reasoning, str) or len(reasoning) < 10:
        return 0.0
        
    try:
        conf = float(output.get("confidence", 0.0))
        # Base confidence must be at least 0.7 to score well
        return conf if conf >= 0.7 else conf / 2.0
    except (TypeError, ValueError):
        return 0.0


@sovereign_quality_gate_async(
    tool_name="architect_arbitration", evaluator=architect_evaluator, threshold=0.8
)
async def _invoke_architect_guarded(
    judge: Any, prompt: str, valid_ids: set[str], reasoning_mode: Any
) -> Result[dict[str, Any], str]:
    """Invoke the architect judge, protected by the sovereign quality gate."""
    try:
        response = await judge(prompt, reasoning_mode=reasoning_mode)
        return Ok(response)
    except TypeError:
        # Fallback if judge doesn't support reasoning_mode kwargs
        response = await judge(prompt)
        return Ok(response)


class DeadlockBreaker:
    """Last-resort heuristic resolver: 0.4×reversibility + 0.3×(1-cost) + 0.3×confidence."""

    __slots__ = ("_budget",)

    def __init__(self, budget: float = 100.0) -> None:
        self._budget = max(budget, 1.0)  # Prevent division by zero

    def resolve(self, options: list[ConflictOption]) -> ResolutionResult:
        """Score all options and pick the winner via heuristic."""
        if not options:
            raise ValueError("Cannot break deadlock with zero options")

        scored: list[tuple[ConflictOption, float]] = []
        for opt in options:
            score = self._heuristic_score(opt)
            scored.append((opt, score))

        # O(N log N) — but N is ≤ 10 for any sane conflict
        scored.sort(key=lambda x: x[1], reverse=True)

        winner, best_score = scored[0]
        runner_up_score = scored[1][1] if len(scored) > 1 else 0.0

        return ResolutionResult(
            winner_id=winner.id,
            method=ResolutionMethod.DEADLOCK_HEURISTIC,
            consensus_level=0.0,
            reasoning=(
                f"Deadlock broken by heuristic: reversibility={winner.reversibility:.2f}, "
                f"cost_ratio={winner.estimated_cost / self._budget:.2f}, "
                f"confidence={winner.confidence:.2f}. "
                f"Score: {best_score:.4f} > {runner_up_score:.4f}"
            ),
            total_weight_for=best_score,
            total_weight_against=runner_up_score,
        )

    def _heuristic_score(self, option: ConflictOption) -> float:
        """Reversibility-biased scoring."""
        rev = option.reversibility * 0.4
        cost = (1.0 - min(option.estimated_cost / self._budget, 1.0)) * 0.3
        conf = option.confidence * 0.3
        return round(rev + cost + conf, 4)


class ConflictResolver:
    """Sovereign Conflict Resolution Engine (4-tier escalation ladder)."""

    CONSENSUS_THRESHOLD: float = 0.70
    ARCHITECT_CONFIDENCE_GATE: float = 0.80

    __slots__ = ("_history", "_deadlock_breaker", "_conflict_counter")

    def __init__(self, budget: float = 100.0) -> None:
        self._history: list[ConflictResolution] = []
        self._deadlock_breaker = DeadlockBreaker(budget=budget)
        self._conflict_counter = 0

    async def resolve(
        self,
        *,
        conflict_type: ConflictType,
        options: list[ConflictOption],
        agents: dict[str, tuple[AgentProfile, str]],  # agent_id → (profile, chosen_option_id)
        conflict_domain: str = "general",
        architect_judge: Any | None = None,
    ) -> ConflictResolution:
        """Execute the full escalation ladder."""
        self._conflict_counter += 1
        conflict_id = self._generate_id()
        now = time.time()
        participants = list(agents.keys())

        logger.info(
            "⚔️ Conflict %s detected: type=%s, %d options, %d agents",
            conflict_id,
            conflict_type.value,
            len(options),
            len(agents),
        )

        # Tier 1: Factual Triangulation
        if conflict_type == ConflictType.FACTUAL:
            result = await self._triangulate(options, agents)
            return self._record(conflict_id, now, conflict_type, participants, options, result)

        # Tier 2: Weighted Voting
        votes, result = self._weighted_vote(options, agents, conflict_domain)

        if result.consensus_level >= self.CONSENSUS_THRESHOLD:
            logger.info(
                "✅ Consensus achieved: %s (%.1f%%)", result.winner_id, result.consensus_level * 100
            )
            record = self._record(conflict_id, now, conflict_type, participants, options, result)
            record.votes = votes
            return record

        logger.warning(
            "⚠️ No consensus (%.1f%% < %.1f%%). Escalating...",
            result.consensus_level * 100,
            self.CONSENSUS_THRESHOLD * 100,
        )

        # Tier 3: Architect Arbitration
        if architect_judge is not None:
            arb_result = await self._architect_arbitrate(options, architect_judge)
            if arb_result is not None:
                record = self._record(
                    conflict_id, now, conflict_type, participants, options, arb_result
                )
                record.votes = votes
                return record

        # Tier 4: Deadlock Heuristic
        logger.warning("🔧 Deadlock: applying heuristic breaker (Ω₆ Zenón's Razor)")
        dl_result = self._deadlock_breaker.resolve(options)
        record = self._record(conflict_id, now, conflict_type, participants, options, dl_result)
        record.votes = votes
        return record

    async def _triangulate(
        self,
        options: list[ConflictOption],
        agents: dict[str, tuple[AgentProfile, str]],
    ) -> ResolutionResult:
        """Resolve factual conflicts by evidence weight."""
        option_votes: dict[str, int] = {o.id: 0 for o in options}
        for _, (_, chosen_id) in agents.items():
            if chosen_id in option_votes:
                option_votes[chosen_id] += 1

        if not option_votes:
            # Edge case: no valid votes
            return ResolutionResult(
                winner_id=options[0].id,
                method=ResolutionMethod.TRIANGULATION,
                consensus_level=0.0,
                reasoning="No valid factual sources; defaulting to first option.",
            )

        # Winner = most independent confirmations
        winner_id = max(option_votes, key=lambda k: option_votes[k])
        total_votes = sum(option_votes.values())
        consensus = option_votes[winner_id] / total_votes if total_votes > 0 else 0.0

        return ResolutionResult(
            winner_id=winner_id,
            method=ResolutionMethod.TRIANGULATION,
            consensus_level=consensus,
            reasoning=f"Factual triangulation: {option_votes[winner_id]}/{total_votes} sources confirm.",
            total_weight_for=float(option_votes[winner_id]),
            total_weight_against=float(total_votes - option_votes[winner_id]),
        )

    def _weighted_vote(
        self,
        options: list[ConflictOption],
        agents: dict[str, tuple[AgentProfile, str]],
        conflict_domain: str,
    ) -> tuple[list[WeightedVote], ResolutionResult]:
        """Execute reputation-weighted voting."""
        # O(1) accumulator per option
        option_weights: dict[str, float] = {o.id: 0.0 for o in options}
        all_votes: list[WeightedVote] = []
        total_weight = 0.0

        for agent_id, (profile, chosen_id) in agents.items():
            vote_template = calculate_vote_weight(profile, conflict_domain)
            if vote_template is None:
                continue

            # Materialize the vote with the chosen option
            vote = WeightedVote(
                agent_id=agent_id,
                option_id=chosen_id,
                weight=vote_template.weight,
                domain_component=vote_template.domain_component,
                track_component=vote_template.track_component,
                confidence_component=vote_template.confidence_component,
                recency_component=vote_template.recency_component,
            )
            all_votes.append(vote)
            total_weight += vote.weight

            if chosen_id in option_weights:
                option_weights[chosen_id] += vote.weight

        if total_weight == 0.0:
            return all_votes, ResolutionResult(
                winner_id=options[0].id if options else "",
                method=ResolutionMethod.WEIGHTED_VOTE,
                consensus_level=0.0,
                reasoning="Zero total weight — no valid voters.",
            )

        # Find winner (O(K) where K = number of options, typically ≤ 5)
        winner_id = max(option_weights, key=lambda k: option_weights[k])
        winner_weight = option_weights[winner_id]
        consensus = winner_weight / total_weight

        return all_votes, ResolutionResult(
            winner_id=winner_id,
            method=ResolutionMethod.WEIGHTED_VOTE,
            consensus_level=consensus,
            reasoning=(
                f"Weighted vote: {winner_id} received {winner_weight:.3f}/{total_weight:.3f} "
                f"({consensus:.1%} consensus)."
            ),
            total_weight_for=winner_weight,
            total_weight_against=total_weight - winner_weight,
        )

    async def _architect_arbitrate(
        self,
        options: list[ConflictOption],
        judge: Any,
    ) -> ResolutionResult | None:
        """Invoke LLM-as-judge for complex strategic decisions."""
        options_desc = "\n".join(
            f"  [{o.id}] {o.description} (reversibility={o.reversibility:.2f}, cost={o.estimated_cost})"
            for o in options
        )
        prompt = (
            "You are the Architect Arbiter. Two or more proposals cannot reach consensus. "
            "Evaluate the trade-offs and select the best option.\n\n"
            f"Options:\n{options_desc}\n\n"
            'Respond with JSON: {"winner_id": "... ", "confidence": 0.0-1.0, "reasoning": "..."}'
        )

        valid_ids = {o.id for o in options}

        # Invoke through the Sovereign Quality Gate
        # Exceptions/detonations are folded into Err implicitly.
        result = await _invoke_architect_guarded(
            judge=judge,
            prompt=prompt,
            valid_ids=valid_ids,
            reasoning_mode=ReasoningMode.DEEP_THINK,
        )

        if result.is_err():
            # Gate triggered, circuit open, or evaluator failed. Fallback to Deadlock Heuristic.
            # The error contains detonation or trace info.
            logger.warning(
                "Architect arbitration rejected by Quality Gate: %s", result.unwrap_or(None)
            )
            return None

        response = result.unwrap()

        confidence = float(response.get("confidence", 0.0))
        winner_id = str(response.get("winner_id", ""))
        reasoning = str(response.get("reasoning", "No reasoning provided"))

        if confidence < self.ARCHITECT_CONFIDENCE_GATE:
            logger.warning(
                "Architect confidence %.2f < gate %.2f — cannot decide",
                confidence,
                self.ARCHITECT_CONFIDENCE_GATE,
            )
            return None

        return ResolutionResult(
            winner_id=winner_id,
            method=ResolutionMethod.ARCHITECT_ARBITRATION,
            consensus_level=confidence,
            reasoning=f"Architect decision (conf={confidence:.2f}): {reasoning}",
        )

    def _record(
        self,
        conflict_id: str,
        timestamp: float,
        conflict_type: ConflictType,
        participants: list[str],
        options: list[ConflictOption],
        result: ResolutionResult,
    ) -> ConflictResolution:
        """Create and archive a ConflictResolution record."""
        record = ConflictResolution(
            conflict_id=conflict_id,
            timestamp=timestamp,
            conflict_type=conflict_type,
            participants=participants,
            options=options,
            resolution=result,
        )
        self._history.append(record)
        logger.info(
            "📋 Conflict %s resolved: winner=%s method=%s consensus=%.1f%%",
            conflict_id,
            result.winner_id,
            result.method.value,
            result.consensus_level * 100,
        )
        return record

    def _generate_id(self) -> str:
        """Generate a deterministic, ordered conflict ID."""
        ts_hex = hashlib.sha256(str(time.time()).encode()).hexdigest()[:6]
        return f"CR-{self._conflict_counter:04d}-{ts_hex}"

    @property
    def history(self) -> list[ConflictResolution]:
        """Read-only access to resolution history."""
        return list(self._history)

    def audit_trail(self) -> list[dict[str, Any]]:
        """Export full audit trail as serializable dicts."""
        return [r.to_dict() for r in self._history]
