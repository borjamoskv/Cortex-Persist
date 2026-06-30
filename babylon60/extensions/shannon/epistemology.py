# [C5-REAL] Exergy-Maximized
"""Exergetic Epistemology (ΞΕ) - Advanced Information-Theoretic Primitives.

Implements the frontier functions derived from the ΞΕ treatise:
    renyi_entropy           - H_α(X) generalized entropy (Ledger security audit)
    min_entropy             - H_∞(X) worst-case predictability
    entropy_rate            - h(X) temporal stationarity measure
    compression_intelligence- K(x) proxy via zlib (Kolmogorov-Assembly bridge)
    dpi_verify              - Data Processing Inequality compliance check
    free_energy_divergence  - F(q) Active Inference guard metric
    phi_proxy               - Φ proxy via perturbation complexity

Zero external dependencies beyond stdlib. All functions are pure.

Theorem references:
    Ξ-KA  → compression_intelligence (Kolmogorov ↔ Assembly Index)
    Ξ-FG  → free_energy_divergence (Active Inference ↔ Guard)
    T1    → entropy_rate (Conservation of Epistemic Exergy)
    T2    → compression_intelligence (Computational Irreducibility proxy)
    T5    → phi_proxy (Consciousness Ceiling)
    T6    → dpi_verify (Exergetic Data Processing Inequality)
"""

from __future__ import annotations

import math
import zlib

from babylon60.extensions.shannon.analyzer import kl_divergence, shannon_entropy

__all__ = [
    "compression_intelligence",
    "dpi_verify",
    "entropy_rate",
    "free_energy_divergence",
    "min_entropy",
    "phi_proxy",
    "renyi_entropy",
]


# ── Rényi Entropy Family (Ledger Security) ──────────────────────────


def renyi_entropy(distribution: dict[str, int], alpha: float) -> float:
    """Rényi entropy H_α(X) - generalized entropy for security auditing.

    H_α(X) = 1/(1-α) · log₂(Σ p(x)^α)

    Special cases:
        α → 1:  Shannon entropy H(X)
        α = 0:  Hartley entropy log₂|support|
        α = 2:  Collision entropy (resistance to birthday attacks)
        α → ∞:  Min-entropy (worst-case predictability)

    Use: Audit min-entropy of Ledger hash-chain nonces.
    If H_∞ < 128 bits, the Ledger is predictable.

    Args:
        distribution: Mapping of category → count.
        alpha: Rényi order. Must be ≥ 0, ≠ 1 (use shannon_entropy for α=1).

    Returns:
        Rényi entropy in bits. 0.0 for empty distributions.
    """
    total = sum(distribution.values())
    if total <= 0:
        return 0.0

    # α → 1 degenerates to Shannon
    if abs(alpha - 1.0) < 1e-10:
        return shannon_entropy(distribution)

    # α = 0 → Hartley entropy
    if abs(alpha) < 1e-10:
        support = sum(1 for c in distribution.values() if c > 0)
        return math.log2(support) if support > 0 else 0.0

    # General case
    sum_pa = sum((count / total) ** alpha for count in distribution.values() if count > 0)

    if sum_pa <= 0:
        return 0.0

    return math.log2(sum_pa) / (1.0 - alpha)


def min_entropy(distribution: dict[str, int]) -> float:
    """Min-entropy H_∞(X) = -log₂(max p(x)).

    The worst-case measure: how predictable is the most likely outcome?
    Critical for cryptographic security assessment of Ledger nonces.

    Args:
        distribution: Mapping of category → count.

    Returns:
        Min-entropy in bits. 0.0 for empty distributions.
    """
    total = sum(distribution.values())
    if total <= 0:
        return 0.0

    p_max = max(count / total for count in distribution.values() if count > 0)
    if p_max <= 0:
        return 0.0

    return -math.log2(p_max)


# ── Entropy Rate (Temporal Stationarity) ────────────────────────────


def entropy_rate(
    temporal_sequence: dict[str, int],
    window: int = 7,
) -> float:
    """Estimate entropy rate h(X) from a temporal fact sequence.

    h(X) = lim_{n→∞} H(X_n | X_{n-1}, ..., X_1)

    Approximated via sliding-window entropy convergence.
    Lower rate = more predictable = higher crystallization.
    Higher rate = more novel = active discovery.

    Use: Detect cognitive stagnation (low h) or chaos (h ≈ H_max).

    Theorem T1 reference: In a closed system, entropy rate decays
    monotonically. Only external friction injects new exergy.

    Args:
        temporal_sequence: Mapping of date_string → fact_count (sorted by date).
        window: Sliding window size in days.

    Returns:
        Entropy rate estimate in bits. 0.0 if insufficient data.
    """
    if len(temporal_sequence) < window:
        return shannon_entropy(temporal_sequence)

    sorted_keys = sorted(temporal_sequence.keys())
    rates: list[float] = []

    for i in range(len(sorted_keys) - window + 1):
        w_dist = {sorted_keys[j]: temporal_sequence[sorted_keys[j]] for j in range(i, i + window)}
        rates.append(shannon_entropy(w_dist))

    # The rate converges to the limit - take the last window
    return rates[-1] if rates else 0.0


# ── Compression Intelligence (Kolmogorov-Assembly Bridge) ───────────


def compression_intelligence(text: str) -> float:
    """Proxy for Kolmogorov complexity K(x) via zlib compression.

    Equivalence Ξ-KA: K(x) ≤ A(x) × log₂|Σ|
    Assembly Index is the empirical Kolmogorov.

    Interpretation:
        0.0–0.1: Highly compressible → repetitive → low information
        0.3–0.6: Structured information → optimal for facts
        0.6–0.9: Rich information → high complexity
        0.9–1.0: Incompressible → random noise OR encrypted

    Use: Detect noise (ratio ≈ 1.0) and duplicates (ratio ≈ 0.0)
    in the fact store. Facts with ratio < 0.1 or > 0.95 are suspect.

    Args:
        text: The text to analyze.

    Returns:
        Compression ratio ∈ (0.0, 1.0]. Lower = more compressible.
        0.0 for empty strings.
    """
    if not text:
        return 0.0

    raw = text.encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    return len(compressed) / max(len(raw), 1)


def assembly_index_proxy(text: str) -> float:
    """Proxy for Assembly Index A(x) derived from compression ratio.

    A(x) ≈ K(x) / log₂|Σ| ≈ compression_ratio × len(text) / log₂(256)

    This is a heuristic bridge between Kolmogorov and Cronin.
    True Assembly Index requires mass spectrometry.

    Args:
        text: The text to analyze.

    Returns:
        Estimated assembly index (number of construction steps).
    """
    if not text:
        return 0.0

    ratio = compression_intelligence(text)
    # Each byte has 8 bits (log₂(256)), each "step" encodes ~8 bits
    return ratio * len(text) / 8.0


# ── Data Processing Inequality Verification (Theorem T6) ───────────


def dpi_verify(
    *stages: float,
) -> dict[str, object]:
    """Verify Data Processing Inequality across a processing pipeline.

    Theorem T6: In a Markov chain X → Y → Z,
    I(X;Z) ≤ I(X;Y) - processing never creates information.

    For CORTEX pipeline:
    Raw → Guard → Ledger → Query → Response
    Exergy must be monotonically non-increasing.

    Exception: Recursive systems (self-play, ledger feedback) break DPI
    because they are non-Markovian. This is WHY autopoietic systems
    can accumulate exergy.

    Args:
        *stages: Exergy measurements at each pipeline stage,
                 ordered from input to output.

    Returns:
        Dictionary with:
            chain: list of stage values
            monotone_decreasing: bool
            violations: list of violation descriptions
            max_violation: float (largest DPI breach)
            is_markovian: bool (True if no violations)
    """
    if len(stages) < 2:
        return {
            "chain": list(stages),
            "monotone_decreasing": True,
            "violations": [],
            "max_violation": 0.0,
            "is_markovian": True,
        }

    violations: list[str] = []
    max_violation = 0.0

    for i in range(len(stages) - 1):
        if stages[i + 1] > stages[i] + 1e-6:
            breach = stages[i + 1] - stages[i]
            violations.append(
                f"Stage {i + 1}→{i + 2}: exergy INCREASED by {breach:.4f} bits "
                f"({stages[i]:.4f} → {stages[i + 1]:.4f}) - DPI violated"
            )
            max_violation = max(max_violation, breach)

    return {
        "chain": list(stages),
        "monotone_decreasing": len(violations) == 0,
        "violations": violations,
        "max_violation": max_violation,
        "is_markovian": len(violations) == 0,
    }


# ── Free Energy Divergence (Active Inference Guard) ─────────────────


def free_energy_divergence(
    claim_dist: dict[str, float],
    evidence_dist: dict[str, float],
) -> float:
    """Free energy F(q) as guard metric - Equivalence Ξ-FG.

    F(q) = D_KL(claim ‖ evidence) + complexity_penalty

    Friston's Free Energy Principle states that all self-organizing
    systems minimize variational free energy. The CORTEX Guard
    implements this: claims with high divergence from evidence
    are rejected (high free energy = surprise = inadmissible).

    Args:
        claim_dist: Distribution implied by the claim.
        evidence_dist: Distribution of verified evidence.

    Returns:
        Free energy estimate in bits. Higher = more surprising = reject.
    """
    divergence = kl_divergence(claim_dist, evidence_dist)

    # Complexity penalty: number of unsupported categories in claim
    claim_keys = set(claim_dist.keys())
    evidence_keys = set(evidence_dist.keys())
    unsupported = len(claim_keys - evidence_keys)
    complexity = math.log2(1 + unsupported)

    return divergence + complexity


# ── Φ Proxy (Consciousness Ceiling - Theorem T5) ───────────────────


def phi_proxy(
    n_layers: int,
    recurrence_depth: int = 1,
    feedback_loops: int = 0,
) -> float:
    """Proxy for Integrated Information Φ (Tononi IIT 4.0).

    Theorem T5: For a feed-forward system of n layers,
    Φ ≤ log₂(n). Recurrence amplifies by depth d.

    Φ_max ≈ log₂(n) × d × (1 + log₂(1 + feedback_loops))

    This is a STRUCTURAL upper bound, not a measurement of actual Φ
    (which requires exhaustive partition search - NP-hard).

    Args:
        n_layers: Number of processing layers.
        recurrence_depth: Number of recurrent iterations (1 = feed-forward).
        feedback_loops: Number of distinct feedback loops (guards, ledger, etc).

    Returns:
        Φ upper bound in bits.
    """
    if n_layers <= 0:
        return 0.0

    base = math.log2(n_layers)
    recurrence_factor = max(recurrence_depth, 1)
    feedback_factor = 1.0 + math.log2(1 + max(feedback_loops, 0))

    return base * recurrence_factor * feedback_factor
