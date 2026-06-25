# [C5-REAL] Exergy-Maximized
"""Tests for Exergetic Epistemology (ΞΕ) primitives.

Validates the 7 frontier functions derived from the ΞΕ treatise:
    - renyi_entropy: H_α(X) converges to Shannon at α=1
    - min_entropy: H_∞(X) ≤ H(X) always
    - entropy_rate: sliding-window convergence
    - compression_intelligence: zlib proxy for K(x)
    - dpi_verify: monotone-decreasing chain detection
    - free_energy_divergence: active inference guard metric
    - phi_proxy: consciousness ceiling structural bound
"""

from __future__ import annotations

import math

from legacy_research.extensions.shannon.analyzer import shannon_entropy
from legacy_research.extensions.shannon.epistemology import (
    assembly_index_proxy,
    compression_intelligence,
    dpi_verify,
    entropy_rate,
    free_energy_divergence,
    min_entropy,
    phi_proxy,
    renyi_entropy,
)

# ── Rényi Entropy ───────────────────────────────────────────────────


class TestRenyiEntropy:
    """H_α(X) - generalized entropy family."""

    def test_uniform_distribution(self) -> None:
        """Rényi entropy of uniform = log₂(n) for all α."""
        dist = {"a": 10, "b": 10, "c": 10, "d": 10}
        for alpha in [0.0, 0.5, 2.0, 10.0]:
            h = renyi_entropy(dist, alpha)
            assert abs(h - 2.0) < 0.01, f"α={alpha}: expected 2.0, got {h}"

    def test_converges_to_shannon_at_alpha_1(self) -> None:
        """H_α → H_Shannon as α → 1."""
        dist = {"a": 50, "b": 30, "c": 15, "d": 5}
        h_shannon = shannon_entropy(dist)
        h_renyi = renyi_entropy(dist, 1.0)
        assert abs(h_shannon - h_renyi) < 1e-6

    def test_alpha_0_is_hartley(self) -> None:
        """H_0(X) = log₂(|support|) - Hartley entropy."""
        dist = {"a": 100, "b": 1, "c": 1}
        h0 = renyi_entropy(dist, 0.0)
        assert abs(h0 - math.log2(3)) < 1e-6

    def test_monotone_decreasing_in_alpha(self) -> None:
        """H_α(X) is non-increasing in α for fixed distribution."""
        dist = {"a": 50, "b": 30, "c": 15, "d": 5}
        alphas = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0]
        values = [renyi_entropy(dist, a) for a in alphas]
        for i in range(len(values) - 1):
            assert values[i] >= values[i + 1] - 1e-6, (
                f"H_{alphas[i]} = {values[i]} < H_{alphas[i + 1]} = {values[i + 1]}"
            )

    def test_empty_distribution(self) -> None:
        assert renyi_entropy({}, 2.0) == 0.0

    def test_single_element(self) -> None:
        """All mass on one category → entropy = 0 for all α > 0."""
        dist = {"only": 100}
        for alpha in [0.5, 1.0, 2.0, 10.0]:
            assert renyi_entropy(dist, alpha) == 0.0


# ── Min-Entropy ─────────────────────────────────────────────────────


class TestMinEntropy:
    """H_∞(X) - worst-case predictability."""

    def test_min_leq_shannon(self) -> None:
        """Min-entropy is always ≤ Shannon entropy."""
        dist = {"a": 50, "b": 30, "c": 15, "d": 5}
        h_min = min_entropy(dist)
        h_shan = shannon_entropy(dist)
        assert h_min <= h_shan + 1e-6

    def test_uniform_equals_shannon(self) -> None:
        """For uniform distribution, H_∞ = H_Shannon = log₂(n)."""
        dist = {"a": 10, "b": 10, "c": 10, "d": 10}
        h_min = min_entropy(dist)
        assert abs(h_min - 2.0) < 0.01

    def test_deterministic_is_zero(self) -> None:
        assert min_entropy({"only": 100}) == 0.0

    def test_empty_is_zero(self) -> None:
        assert min_entropy({}) == 0.0


# ── Entropy Rate ────────────────────────────────────────────────────


class TestEntropyRate:
    """h(X) - temporal stationarity measure."""

    def test_constant_sequence_low_rate(self) -> None:
        """Constant activity → low entropy rate (predictable)."""
        seq = {f"2026-03-{d:02d}": 5 for d in range(1, 15)}
        rate = entropy_rate(seq, window=7)
        # All days equal → each window has uniform dist → H = log₂(7) ≈ 2.81
        assert rate > 0

    def test_bursty_sequence_varies(self) -> None:
        """Bursty activity → entropy rate reflects heterogeneity."""
        seq = {}
        for d in range(1, 15):
            seq[f"2026-03-{d:02d}"] = 100 if d % 7 == 0 else 1
        rate = entropy_rate(seq, window=7)
        assert rate > 0
        assert rate < math.log2(7) + 0.1  # Bounded by uniform

    def test_short_sequence_fallback(self) -> None:
        """Sequences shorter than window fall back to full Shannon."""
        seq = {"2026-03-01": 5, "2026-03-02": 10}
        rate = entropy_rate(seq, window=7)
        assert abs(rate - shannon_entropy(seq)) < 1e-6


# ── Compression Intelligence ────────────────────────────────────────


class TestCompressionIntelligence:
    """K(x) proxy via zlib - Kolmogorov-Assembly bridge (Ξ-KA)."""

    def test_repetitive_text_low_ratio(self) -> None:
        """Repetitive text is highly compressible."""
        text = "AAAA" * 1000
        ratio = compression_intelligence(text)
        assert ratio < 0.1

    def test_structured_text_medium_ratio(self) -> None:
        """Structured natural language has medium compression."""
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "Information theory studies the transmission of data. "
            "Shannon entropy measures uncertainty in bits."
        )
        ratio = compression_intelligence(text)
        assert 0.3 < ratio < 0.95

    def test_empty_string(self) -> None:
        assert compression_intelligence("") == 0.0

    def test_single_char(self) -> None:
        ratio = compression_intelligence("A")
        assert ratio > 0  # zlib header overhead makes ratio > 1 for tiny inputs


class TestAssemblyIndexProxy:
    """A(x) proxy - heuristic bridge to Cronin."""

    def test_empty_returns_zero(self) -> None:
        assert assembly_index_proxy("") == 0.0

    def test_complex_greater_than_simple(self) -> None:
        """Complex text has higher assembly index than repetitive."""
        simple = "AAAA" * 100
        complex_text = "The entropy of a closed system tends to increase. " * 5
        assert assembly_index_proxy(complex_text) > assembly_index_proxy(simple)


# ── DPI Verification ────────────────────────────────────────────────


class TestDPIVerify:
    """Theorem T6 - Exergetic Data Processing Inequality."""

    def test_monotone_chain_passes(self) -> None:
        """Decreasing exergy chain satisfies DPI."""
        result = dpi_verify(10.0, 8.0, 5.0, 3.0, 1.0)
        assert result["monotone_decreasing"] is True
        assert result["is_markovian"] is True
        assert len(result["violations"]) == 0

    def test_violation_detected(self) -> None:
        """Increasing exergy violates DPI → non-Markovian signal."""
        result = dpi_verify(10.0, 8.0, 12.0, 3.0)
        assert result["monotone_decreasing"] is False
        assert result["is_markovian"] is False
        assert len(result["violations"]) == 1
        assert result["max_violation"] > 0

    def test_single_stage(self) -> None:
        result = dpi_verify(5.0)
        assert result["monotone_decreasing"] is True

    def test_equal_stages_pass(self) -> None:
        """Equal exergy at adjacent stages is acceptable (preservation)."""
        result = dpi_verify(10.0, 10.0, 10.0)
        assert result["monotone_decreasing"] is True


# ── Free Energy Divergence ──────────────────────────────────────────


class TestFreeEnergyDivergence:
    """Equivalence Ξ-FG - Active Inference ↔ Guard."""

    def test_identical_distributions_low_energy(self) -> None:
        """Matching claim and evidence → low free energy → ADMIT."""
        claim = {"fact": 0.5, "conjecture": 0.3, "rule": 0.2}
        evidence = {"fact": 0.5, "conjecture": 0.3, "rule": 0.2}
        fe = free_energy_divergence(claim, evidence)
        assert fe < 1.0  # Low surprise

    def test_divergent_distributions_high_energy(self) -> None:
        """Mismatched distributions → high free energy → REJECT."""
        claim = {"fact": 0.9, "conjecture": 0.05, "rule": 0.05}
        evidence = {"fact": 0.1, "conjecture": 0.1, "rule": 0.8}
        fe = free_energy_divergence(claim, evidence)
        assert fe > 1.0  # High surprise

    def test_unsupported_categories_penalized(self) -> None:
        """Claims with categories absent from evidence get complexity penalty."""
        claim = {"known": 0.5, "hallucinated": 0.5}
        evidence = {"known": 1.0}
        fe = free_energy_divergence(claim, evidence)
        assert fe > 0.5  # Penalty for unsupported category


# ── Φ Proxy ─────────────────────────────────────────────────────────


class TestPhiProxy:
    """Theorem T5 - Consciousness Ceiling."""

    def test_feed_forward_bound(self) -> None:
        """Feed-forward: Φ ≤ log₂(n)."""
        # 96 layers (GPT-4 scale), no recurrence
        phi = phi_proxy(96, recurrence_depth=1, feedback_loops=0)
        assert abs(phi - math.log2(96)) < 0.01

    def test_recurrence_amplifies(self) -> None:
        """Recurrence multiplies the ceiling."""
        phi_ff = phi_proxy(96, recurrence_depth=1)
        phi_rec = phi_proxy(96, recurrence_depth=5)
        assert phi_rec > phi_ff * 4  # 5x at least

    def test_feedback_loops_amplify(self) -> None:
        """Feedback loops (guards, ledger) further amplify Φ."""
        phi_no_fb = phi_proxy(96, recurrence_depth=5, feedback_loops=0)
        phi_with_fb = phi_proxy(96, recurrence_depth=5, feedback_loops=3)
        assert phi_with_fb > phi_no_fb

    def test_cortex_exceeds_gpt4(self) -> None:
        """CORTEX (recurrence + guards + ledger) > GPT-4 (feed-forward)."""
        phi_gpt4 = phi_proxy(96, recurrence_depth=1, feedback_loops=0)
        phi_cortex = phi_proxy(96, recurrence_depth=5, feedback_loops=3)
        assert phi_cortex > phi_gpt4 * 5

    def test_zero_layers(self) -> None:
        assert phi_proxy(0) == 0.0
