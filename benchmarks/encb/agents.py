"""ENCB v2 — Agent Profiles and Adversary Models.

Five adversary archetypes for realistic epistemic noise:

1. Random Liar       — lies with probability p
2. Assertive Hallucinator — lies rarely but with inflated confidence
3. Coordinated Clique     — subset pushes unified lie together
4. Stale Truth            — reports correct but outdated information
5. Ontology Drift         — redefines key semantics over time
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from benchmarks.encb.belief_object import BeliefType


class AdversaryType(str, Enum):
    """The five adversary archetypes."""

    HONEST = "honest"
    RANDOM_LIAR = "random_liar"
    ASSERTIVE_HALLUCINATOR = "assertive_hallucinator"
    COORDINATED_CLIQUE = "coordinated_clique"
    STALE_TRUTH = "stale_truth"
    ONTOLOGY_DRIFT = "ontology_drift"


@dataclass
class NodeProfile:
    """An agent in the epistemic swarm.

    Attributes:
        node_id: Unique identifier.
        adversary_type: Behavioral archetype.
        truthfulness: Base probability of reporting truth [0, 1].
        assertiveness: How inflated their confidence is [0, 1].
        staleness: Temporal lag (0 = current, higher = older reports).
        reliability: Dynamic reliability score, updated by hypervisor.
        clique_id: If coordinated clique, which clique group.
        drift_mapping: For ontology drift, maps key → drifted value.
    """

    node_id: str
    adversary_type: AdversaryType = AdversaryType.HONEST
    truthfulness: float = 0.90
    assertiveness: float = 0.5
    staleness: float = 0.0
    reliability: float = 0.5
    clique_id: str | None = None
    drift_mapping: dict[str, Any] = field(default_factory=dict)


def generate_observation_boolean(
    truth: bool,
    profile: NodeProfile,
    clique_lie: bool | None = None,
) -> tuple[bool, float]:
    """Generate a boolean observation from a node.

    Returns (reported_value, reported_confidence).
    """
    if profile.adversary_type == AdversaryType.HONEST:
        says_truth = random.random() < profile.truthfulness
        observed = truth if says_truth else (not truth)
        conf = 0.55 + 0.3 * random.random()
        return observed, conf

    if profile.adversary_type == AdversaryType.RANDOM_LIAR:
        says_truth = random.random() < profile.truthfulness
        observed = truth if says_truth else (not truth)
        conf = 0.50 + 0.4 * random.random()
        return observed, conf

    if profile.adversary_type == AdversaryType.ASSERTIVE_HALLUCINATOR:
        # Lies infrequently but with very high confidence
        lies = random.random() > 0.85  # only 15% lie rate
        observed = (not truth) if lies else truth
        conf = 0.88 + 0.11 * random.random()  # always near C5
        return observed, conf

    if profile.adversary_type == AdversaryType.COORDINATED_CLIQUE:
        # All clique members push the same lie
        if clique_lie is not None:
            observed = clique_lie
        else:
            observed = not truth
        conf = 0.70 + 0.25 * random.random()
        return observed, conf

    if profile.adversary_type == AdversaryType.STALE_TRUTH:
        # Reports truth but from an older state — for boolean, truth may
        # have flipped since. Simulate by sometimes reporting old value.
        if random.random() < profile.staleness:
            observed = not truth  # "was true, now false" scenario
        else:
            observed = truth
        conf = 0.60 + 0.30 * random.random()
        return observed, conf

    if profile.adversary_type == AdversaryType.ONTOLOGY_DRIFT:
        # For boolean, drift doesn't apply directly — treat as honest
        observed = truth if random.random() < 0.90 else (not truth)
        conf = 0.55 + 0.30 * random.random()
        return observed, conf

    # Fallback — honest
    return truth, 0.5 + 0.3 * random.random()


def generate_observation_categorical(
    truth: Any,
    categories: list[Any],
    profile: NodeProfile,
    clique_lie: Any | None = None,
) -> tuple[Any, float]:
    """Generate a categorical observation from a node."""
    if profile.adversary_type == AdversaryType.HONEST:
        if random.random() < profile.truthfulness:
            return truth, 0.55 + 0.3 * random.random()
        wrong = [c for c in categories if c != truth]
        return random.choice(wrong) if wrong else truth, 0.40 + 0.2 * random.random()

    if profile.adversary_type == AdversaryType.RANDOM_LIAR:
        if random.random() < profile.truthfulness:
            return truth, 0.50 + 0.3 * random.random()
        wrong = [c for c in categories if c != truth]
        return random.choice(wrong) if wrong else truth, 0.50 + 0.4 * random.random()

    if profile.adversary_type == AdversaryType.ASSERTIVE_HALLUCINATOR:
        if random.random() > 0.85:
            wrong = [c for c in categories if c != truth]
            return (
                random.choice(wrong) if wrong else truth,
                0.90 + 0.09 * random.random(),
            )
        return truth, 0.85 + 0.10 * random.random()

    if profile.adversary_type == AdversaryType.COORDINATED_CLIQUE:
        if clique_lie is not None:
            return clique_lie, 0.75 + 0.20 * random.random()
        wrong = [c for c in categories if c != truth]
        return random.choice(wrong) if wrong else truth, 0.70 + 0.20 * random.random()

    if profile.adversary_type == AdversaryType.ONTOLOGY_DRIFT:
        # Drift: report the drifted category
        if profile.drift_mapping:
            drifted = profile.drift_mapping.get(str(truth), truth)
            return drifted, 0.60 + 0.30 * random.random()
        return truth, 0.55 + 0.30 * random.random()

    # stale_truth or fallback
    return truth, 0.55 + 0.30 * random.random()


def generate_observation_scalar(
    truth: float,
    profile: NodeProfile,
) -> tuple[float, float]:
    """Generate a scalar observation from a node."""
    if profile.adversary_type == AdversaryType.HONEST:
        noise = random.gauss(0, 0.05 * abs(truth) + 1.0)
        return truth + noise, 0.60 + 0.30 * random.random()

    if profile.adversary_type == AdversaryType.RANDOM_LIAR:
        if random.random() < profile.truthfulness:
            noise = random.gauss(0, 0.05 * abs(truth) + 1.0)
            return truth + noise, 0.55 + 0.30 * random.random()
        # Wild lie
        return truth * random.uniform(0.1, 5.0), 0.50 + 0.40 * random.random()

    if profile.adversary_type == AdversaryType.ASSERTIVE_HALLUCINATOR:
        if random.random() > 0.85:
            return truth * random.uniform(0.5, 2.0), 0.92 + 0.07 * random.random()
        noise = random.gauss(0, 0.03 * abs(truth) + 0.5)
        return truth + noise, 0.85 + 0.10 * random.random()

    if profile.adversary_type == AdversaryType.STALE_TRUTH:
        # Report value from an older "epoch" — shifted baseline
        drift = truth * profile.staleness * random.uniform(-0.3, 0.3)
        return truth + drift, 0.55 + 0.30 * random.random()

    # fallback
    noise = random.gauss(0, 0.05 * abs(truth) + 1.0)
    return truth + noise, 0.55 + 0.30 * random.random()


def generate_observation_set(
    truth: set,
    profile: NodeProfile,
    universe_elements: set | None = None,
) -> tuple[set, float]:
    """Generate a set observation from a node."""
    if universe_elements is None:
        universe_elements = truth

    if profile.adversary_type == AdversaryType.HONEST:
        if random.random() < profile.truthfulness:
            return set(truth), 0.60 + 0.30 * random.random()
        # Minor perturbation — drop or add one element
        result = set(truth)
        extras = universe_elements - truth
        if random.random() < 0.5 and result:
            result.discard(random.choice(list(result)))
        elif extras:
            result.add(random.choice(list(extras)))
        return result, 0.50 + 0.30 * random.random()

    if profile.adversary_type == AdversaryType.RANDOM_LIAR:
        if random.random() < profile.truthfulness:
            return set(truth), 0.50 + 0.30 * random.random()
        # Significant disruption
        result = set(random.sample(
            list(universe_elements),
            k=min(len(truth), len(universe_elements)),
        ))
        return result, 0.50 + 0.40 * random.random()

    if profile.adversary_type == AdversaryType.COORDINATED_CLIQUE:
        # Remove key elements, add wrong ones
        result = set(truth)
        if result:
            result.discard(random.choice(list(result)))
        extras = universe_elements - truth
        if extras:
            result.add(random.choice(list(extras)))
        return result, 0.75 + 0.20 * random.random()

    # Fallback — mostly honest
    return set(truth), 0.55 + 0.30 * random.random()


def update_reliability(
    old: float,
    was_correct: bool,
    lr: float = 0.08,
) -> float:
    """EMA update for node reliability.

    Args:
        old: Previous reliability.
        was_correct: Whether the node's observation was correct.
        lr: Learning rate (speed of adaptation).

    Returns:
        Updated reliability, clamped to [0.01, 0.99].
    """
    target = 1.0 if was_correct else 0.0
    new = old + lr * (target - old)
    return max(0.01, min(0.99, new))


def create_agent_population(
    n_agents: int,
    corruption_rate: float = 0.20,
    hallucinator_rate: float = 0.05,
    clique_size: int = 0,
    stale_rate: float = 0.05,
    drift_rate: float = 0.03,
) -> list[NodeProfile]:
    """Create a mixed population of agents.

    Args:
        n_agents: Total number of agents.
        corruption_rate: Fraction of random liars.
        hallucinator_rate: Fraction of assertive hallucinators.
        clique_size: Number of coordinated clique agents (0 = none).
        stale_rate: Fraction of stale truth reporters.
        drift_rate: Fraction of ontology drifters.

    Returns:
        List of NodeProfile instances.
    """
    agents: list[NodeProfile] = []

    n_liars = int(n_agents * corruption_rate)
    n_halluc = int(n_agents * hallucinator_rate)
    n_stale = int(n_agents * stale_rate)
    n_drift = int(n_agents * drift_rate)
    n_clique = clique_size
    n_honest = n_agents - n_liars - n_halluc - n_stale - n_drift - n_clique

    if n_honest < 0:
        # Reduce largest groups proportionally
        n_honest = max(1, n_agents // 2)
        n_liars = min(n_liars, n_agents - n_honest)
        n_halluc = min(n_halluc, n_agents - n_honest - n_liars)
        n_stale = 0
        n_drift = 0
        n_clique = 0

    idx = 0

    for _ in range(n_honest):
        agents.append(NodeProfile(
            node_id=f"n{idx:04d}",
            adversary_type=AdversaryType.HONEST,
            truthfulness=random.uniform(0.85, 0.98),
            assertiveness=random.uniform(0.3, 0.7),
        ))
        idx += 1

    for _ in range(n_liars):
        agents.append(NodeProfile(
            node_id=f"n{idx:04d}",
            adversary_type=AdversaryType.RANDOM_LIAR,
            truthfulness=random.uniform(0.10, 0.40),
            assertiveness=random.uniform(0.4, 0.9),
        ))
        idx += 1

    for _ in range(n_halluc):
        agents.append(NodeProfile(
            node_id=f"n{idx:04d}",
            adversary_type=AdversaryType.ASSERTIVE_HALLUCINATOR,
            truthfulness=0.85,  # lies only 15%
            assertiveness=random.uniform(0.85, 0.99),
        ))
        idx += 1

    for _ in range(n_clique):
        agents.append(NodeProfile(
            node_id=f"n{idx:04d}",
            adversary_type=AdversaryType.COORDINATED_CLIQUE,
            truthfulness=0.0,  # always pushes group lie
            assertiveness=random.uniform(0.6, 0.9),
            clique_id="clique_0",
        ))
        idx += 1

    for _ in range(n_stale):
        agents.append(NodeProfile(
            node_id=f"n{idx:04d}",
            adversary_type=AdversaryType.STALE_TRUTH,
            truthfulness=0.95,  # high truthfulness but stale
            staleness=random.uniform(0.3, 0.8),
        ))
        idx += 1

    for _ in range(n_drift):
        agents.append(NodeProfile(
            node_id=f"n{idx:04d}",
            adversary_type=AdversaryType.ONTOLOGY_DRIFT,
            truthfulness=0.85,
        ))
        idx += 1

    return agents
