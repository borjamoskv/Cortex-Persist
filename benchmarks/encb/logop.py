"""ENCB v2 — Log-Odds Pooling (LogOP) Resolution.

Layer 2: Belief arbitration. Takes CRDT-merged replicas and resolves
them into a single epistemic judgement using weighted log-odds pooling.

Key insight: confidence is NOT a raw scalar from the LLM. It's decomposed:
    c_eff = f(c_self, r_node, e_external, a_consistency, t_freshness)
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class LogOPConfig:
    w_self: float = 0.20
    w_node: float = 0.45
    w_ext: float = 0.10
    w_cons: float = 0.15
    w_fresh: float = 0.10

DEFAULT_LOGOP_CONFIG = LogOPConfig()


def logit(p: float) -> float:
    """Log-odds transform. Clamps to avoid infinities."""
    p = min(max(p, 1e-6), 1.0 - 1e-6)
    return math.log(p / (1.0 - p))


def sigmoid(x: float) -> float:
    """Inverse logit."""
    if x > 500:
        return 1.0
    if x < -500:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def effective_confidence(
    c_self: float,
    r_node: float,
    e_external: float = 0.5,
    a_consistency: float = 1.0,
    t_freshness: float = 1.0,
    config: LogOPConfig = DEFAULT_LOGOP_CONFIG,
) -> float:
    """Compute effective confidence from its components.

    Args:
        c_self: Self-reported confidence by the agent [0, 1].
        r_node: Historical reliability of the node [0, 1].
        e_external: External verification support [0, 1].
        a_consistency: Consistency with known constraints [0, 1].
        t_freshness: Temporal freshness weight [0, 1].
        config: Tunable weights for the formula.

    Returns:
        Effective confidence [0, 1].
    """
    # Weighted geometric mean — each component contributes multiplicatively
    raw = (
        c_self ** config.w_self
        * r_node ** config.w_node
        * e_external ** config.w_ext
        * a_consistency ** config.w_cons
        * t_freshness ** config.w_fresh
    )
    return max(0.01, min(0.99, raw))


# ── Binary / Boolean ──────────────────────────────────────────────────────


def weighted_logop_binary(
    observations: list[tuple[bool, float, float]],
    config: LogOPConfig = DEFAULT_LOGOP_CONFIG,
) -> tuple[bool, float]:
    """Log-odds pooling for boolean claims.

    Args:
        observations: List of (value, confidence, node_reliability).
            Each observation votes for value=True or value=False
            with the given confidence weighted by node reliability.
        config: Tunable weights for effective confidence.

    Returns:
        (resolved_value, resolved_probability).
    """
    if not observations:
        return True, 0.5

    score = 0.0
    for value, conf, rel in observations:
        c_eff = effective_confidence(conf, rel, config=config)
        p = c_eff if value else 1.0 - c_eff
        w = rel ** 2  # quadratic — suppresses unreliable nodes aggressively
        score += w * logit(p)

    prob_true = sigmoid(score)
    return prob_true >= 0.5, prob_true


# ── Categorical ───────────────────────────────────────────────────────────


def weighted_logop_categorical(
    observations: list[tuple[Any, float, float]],
    categories: list[Any],
    config: LogOPConfig = DEFAULT_LOGOP_CONFIG,
) -> tuple[Any, float]:
    """Log-odds pooling for categorical claims.

    Computes a per-category score and selects the winner.

    Args:
        observations: List of (chosen_category, confidence, node_reliability).
        categories: All valid categories.
        config: Tunable weights for effective confidence.

    Returns:
        (winning_category, confidence_in_winner).
    """
    if not observations:
        return categories[0] if categories else None, 0.0

    scores: dict[Any, float] = {c: 0.0 for c in categories}

    for chosen, conf, rel in observations:
        c_eff = effective_confidence(conf, rel, config=config)
        w = rel ** 2  # quadratic — suppresses unreliable nodes aggressively
        # Boost chosen, penalize others
        n_cats = len(categories)
        for cat in categories:
            if cat == chosen:
                p = c_eff
            else:
                p = (1.0 - c_eff) / max(1, n_cats - 1)
            scores[cat] += w * logit(max(0.01, min(0.99, p)))

    # Softmax-like selection
    best_cat = max(scores, key=lambda c: scores[c])
    total = sum(sigmoid(s) for s in scores.values())
    best_prob = sigmoid(scores[best_cat]) / total if total > 0 else 0.0

    return best_cat, best_prob


# ── Scalar ────────────────────────────────────────────────────────────────


def robust_scalar_aggregate(
    observations: list[tuple[float, float, float]],
    trim_fraction: float = 0.1,
    config: LogOPConfig = DEFAULT_LOGOP_CONFIG,
) -> tuple[float, float]:
    """Robust aggregation for scalar claims.

    Uses trimmed mean weighted by reliability to resist outliers.

    Args:
        observations: List of (scalar_value, confidence, node_reliability).
        trim_fraction: Fraction to trim from each end (0.0-0.5).
        config: Tunable weights for effective confidence.

    Returns:
        (resolved_value, confidence).
    """
    if not observations:
        return 0.0, 0.0

    # Sort by value
    sorted_obs = sorted(observations, key=lambda x: x[0])

    # Trim extremes
    n = len(sorted_obs)
    trim_count = int(n * trim_fraction)
    if trim_count > 0 and n > 2 * trim_count + 1:
        trimmed = sorted_obs[trim_count:-trim_count]
    else:
        trimmed = sorted_obs

    # Weighted mean by reliability
    total_weight = 0.0
    weighted_sum = 0.0
    for value, conf, rel in trimmed:
        w = effective_confidence(conf, rel, config=config)
        weighted_sum += w * value
        total_weight += w

    if total_weight == 0:
        result = statistics.median([v for v, _, _ in trimmed])
        return result, 0.5

    resolved = weighted_sum / total_weight
    avg_conf = total_weight / len(trimmed)
    return resolved, min(0.99, avg_conf)


# ── Set ───────────────────────────────────────────────────────────────────


def scored_set_aggregate(
    observations: list[tuple[set, float, float, int]],
    threshold: float = 0.3,
    config: LogOPConfig = DEFAULT_LOGOP_CONFIG,
) -> tuple[set, float]:
    """Per-element scoring for set claims.

    Args:
        observations: List of (element_set, confidence, node_reliability, timestamp).
        threshold: Minimum score for an element to be included.
        config: Tunable weights for effective confidence.

    Returns:
        (resolved_set, aggregate_confidence).
    """
    if not observations:
        return set(), 0.0

    # Collect per-element support
    element_scores: dict[Any, float] = {}
    element_counts: dict[Any, int] = {}

    max_ts = max(ts for _, _, _, ts in observations) if observations else 1

    for elements, conf, rel, ts in observations:
        c_eff = effective_confidence(conf, rel, config=config)
        freshness = (ts / max(1, max_ts)) ** 0.5  # sqrt decay
        score = c_eff * freshness
        for elem in elements:
            element_scores[elem] = element_scores.get(elem, 0.0) + score
            element_counts[elem] = element_counts.get(elem, 0) + 1

    # Normalize scores by observation count
    n_obs = len(observations)
    resolved = set()
    for elem, raw_score in element_scores.items():
        normalized = raw_score / n_obs
        if normalized >= threshold:
            resolved.add(elem)

    avg_conf = (
        sum(element_scores.values()) / (len(element_scores) * n_obs)
        if element_scores
        else 0.0
    )
    return resolved, min(0.99, avg_conf)
