"""Shannon Information Theory — Pure Math Module.

Zero external dependencies. All functions operate on dict frequency
distributions using only stdlib math.log2.

Functions:
    shannon_entropy             — H(X) in bits
    max_entropy                 — log₂(n)
    normalized_entropy          — H(X) / H_max ∈ [0, 1]
    kl_divergence               — D_KL(P‖Q) with Laplace smoothing
    jensen_shannon_divergence   — JSD(P‖Q) symmetric metric
    mutual_information          — I(X;Y) from joint frequencies
    conditional_entropy         — H(Y|X) from joint frequencies
    cross_entropy               — H(P, Q) cross-entropy
    redundancy                  — R = 1 - H/H_max
    information_value           — Self-information -log₂(p) for a single event
"""

from __future__ import annotations

import math

__all__ = [
    "conditional_entropy",
    "cross_entropy",
    "information_value",
    "jensen_shannon_divergence",
    "kl_divergence",
    "max_entropy",
    "mutual_information",
    "normalized_entropy",
    "redundancy",
    "shannon_entropy",
]


def shannon_entropy(distribution: dict[str, int]) -> float:
    """Compute Shannon entropy H(X) in bits from a frequency distribution.

    H(X) = -Σ p(x) · log₂(p(x))

    Args:
        distribution: Mapping of category → count.

    Returns:
        Entropy in bits. 0.0 for empty or single-element distributions.
    """
    total = sum(distribution.values())
    if total <= 0:
        return 0.0

    h = 0.0
    for count in distribution.values():
        if count > 0:
            p = count / total
            h -= p * math.log2(p)
    return h


def max_entropy(n: int) -> float:
    """Maximum possible entropy for n categories (uniform distribution).

    H_max = log₂(n)

    Args:
        n: Number of distinct categories.

    Returns:
        Maximum entropy in bits. 0.0 if n <= 1.
    """
    if n <= 1:
        return 0.0
    return math.log2(n)


def normalized_entropy(distribution: dict[str, int]) -> float:
    """Normalized entropy H(X) / H_max ∈ [0.0, 1.0].

    Measures how uniformly spread the distribution is.
    1.0 = perfectly uniform. 0.0 = all mass on one category.

    Args:
        distribution: Mapping of category → count.

    Returns:
        Normalized entropy. 0.0 for degenerate distributions.
    """
    n = len(distribution)
    h_max = max_entropy(n)
    if h_max < 1e-15:
        return 0.0
    return shannon_entropy(distribution) / h_max


def redundancy(distribution: dict[str, int]) -> float:
    """Redundancy R = 1 - H(X)/H_max ∈ [0.0, 1.0].

    Measures the fraction of maximum information capacity being wasted.
    0.0 = no redundancy (perfectly uniform).
    1.0 = total redundancy (all mass on one category).

    Args:
        distribution: Mapping of category → count.

    Returns:
        Redundancy score. 0.0 for empty or single-element distributions.
    """
    n = len(distribution)
    h_max = max_entropy(n)
    if h_max < 1e-15:
        return 0.0
    return 1.0 - (shannon_entropy(distribution) / h_max)


def kl_divergence(
    p: dict[str, float],
    q: dict[str, float],
    *,
    smoothing: float = 1e-10,
) -> float:
    """Kullback-Leibler divergence D_KL(P‖Q) with Laplace smoothing.

    D_KL(P‖Q) = Σ P(x) · log₂(P(x) / Q(x))

    NOTE: Not symmetric — D_KL(P‖Q) ≠ D_KL(Q‖P).

    Args:
        p: True distribution (probability dict, values should sum to ~1).
        q: Approximate distribution (probability dict).
        smoothing: Additive smoothing to prevent log(0).

    Returns:
        KL divergence in bits. Always ≥ 0.
    """
    all_keys = set(p) | set(q)
    if not all_keys:
        return 0.0

    d_kl = 0.0
    for key in all_keys:
        p_val = p.get(key, 0.0) + smoothing
        q_val = q.get(key, 0.0) + smoothing
        d_kl += p_val * math.log2(p_val / q_val)
    return max(d_kl, 0.0)  # Numerical stability


def jensen_shannon_divergence(
    p: dict[str, float],
    q: dict[str, float],
) -> float:
    """Jensen-Shannon divergence — symmetric, bounded KL metric.

    JSD(P‖Q) = ½·D_KL(P‖M) + ½·D_KL(Q‖M)  where M = ½(P+Q)

    Unlike KL, JSD is symmetric and always ∈ [0, 1] (when using log₂).
    √JSD is a proper distance metric.

    Args:
        p: First probability distribution.
        q: Second probability distribution.

    Returns:
        JSD in bits. 0.0 for identical distributions. ∈ [0.0, 1.0].
    """
    all_keys = set(p) | set(q)
    if not all_keys:
        return 0.0

    # Build midpoint M = ½(P + Q)
    m: dict[str, float] = {}
    for key in all_keys:
        m[key] = 0.5 * (p.get(key, 0.0) + q.get(key, 0.0))

    jsd = 0.5 * kl_divergence(p, q) + 0.5 * kl_divergence(q, p)
    # Clamp to [0, 1] for numerical stability
    return max(0.0, min(jsd, 1.0))


def mutual_information(joint: dict[tuple[str, str], int]) -> float:
    """Mutual information I(X;Y) from a joint frequency table.

    I(X;Y) = H(X) + H(Y) - H(X,Y)

    Measures how much knowing X reveals about Y (and vice versa).
    I(X;Y) = 0 ⟹ X and Y are independent.

    Args:
        joint: Mapping of (x_value, y_value) → count.

    Returns:
        Mutual information in bits. Always ≥ 0.
    """
    if not joint:
        return 0.0

    total = sum(joint.values())
    if total <= 0:
        return 0.0

    # Marginal distributions
    margin_x: dict[str, int] = {}
    margin_y: dict[str, int] = {}
    for (x, y), count in joint.items():
        margin_x[x] = margin_x.get(x, 0) + count
        margin_y[y] = margin_y.get(y, 0) + count

    h_x = shannon_entropy(margin_x)
    h_y = shannon_entropy(margin_y)

    # Joint entropy H(X,Y) — treat tuple keys as flat categories
    joint_flat: dict[str, int] = {f"{x}|{y}": c for (x, y), c in joint.items()}
    h_xy = shannon_entropy(joint_flat)

    mi = h_x + h_y - h_xy
    return max(mi, 0.0)  # Numerical stability


def conditional_entropy(
    joint: dict[tuple[str, str], int],
) -> float:
    """Conditional entropy H(Y|X) from a joint frequency table.

    H(Y|X) = H(X,Y) - H(X)

    Measures the remaining uncertainty in Y after observing X.
    H(Y|X) = 0 ⟹ X completely determines Y.
    H(Y|X) = H(Y) ⟹ X and Y are independent.

    Args:
        joint: Mapping of (x_value, y_value) → count.

    Returns:
        Conditional entropy in bits. Always ≥ 0.
    """
    if not joint:
        return 0.0

    # Marginal H(X)
    margin_x: dict[str, int] = {}
    for (x, _y), count in joint.items():
        margin_x[x] = margin_x.get(x, 0) + count
    h_x = shannon_entropy(margin_x)

    # Joint H(X,Y)
    joint_flat: dict[str, int] = {f"{x}|{y}": c for (x, y), c in joint.items()}
    h_xy = shannon_entropy(joint_flat)

    return max(h_xy - h_x, 0.0)  # Numerical stability


def cross_entropy(
    p: dict[str, float],
    q: dict[str, float],
    *,
    smoothing: float = 1e-10,
) -> float:
    """Cross-entropy H(P, Q) = -Σ P(x) · log₂(Q(x)).

    Measures the average number of bits needed to encode events from P
    using the code optimized for Q. Always ≥ H(P).

    H(P, Q) = H(P) + D_KL(P‖Q)

    Args:
        p: True distribution (probability dict).
        q: Model distribution (probability dict).
        smoothing: Additive smoothing to prevent log(0).

    Returns:
        Cross-entropy in bits. Always ≥ 0.
    """
    all_keys = set(p) | set(q)
    if not all_keys:
        return 0.0

    ce = 0.0
    for key in all_keys:
        p_val = p.get(key, 0.0)
        q_val = q.get(key, 0.0) + smoothing
        if p_val > 0:
            ce -= p_val * math.log2(q_val)
    return max(ce, 0.0)


def information_value(freq: int, total: int) -> float:
    """Self-information (surprisal) for a single event.

    I(x) = -log₂(p(x)) = -log₂(freq / total)

    Rarer events carry more information.

    Args:
        freq: Frequency of this event.
        total: Total number of events.

    Returns:
        Self-information in bits. 0.0 if freq <= 0 or total <= 0.
    """
    if freq <= 0 or total <= 0:
        return 0.0
    p = freq / total
    return -math.log2(p)
