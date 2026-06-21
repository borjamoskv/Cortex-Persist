# [C5-REAL] Exergy-Maximized
"""
Semantic Entropy Scorer (Informational Entropy Layer)
Thermodynamic bounds for semantic compression and node collapse.
"""

import math
import re
import zlib
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class CollapseVerdict:
    """Deterministic result of an evaluate_collapse evaluation."""
    approved: bool
    reason: str
    post_collapse_mass: float
    post_collapse_entropy: float


class SemanticEntropyScorer:
    """
    Implements the Informational Entropy Layer.
    Measures semantic complexity to trigger collapse (Kolmogorov compression)
    across redundant nodes, bound by thermodynamic invariants I4, I5, I6.
    """

    MAX_KINETIC_MULTIPLIER = 2.0
    KL_DIVERGENCE_THRESHOLD = 0.05
    MASS_DIFFERENCE_THRESHOLD = 0.1

    def _get_frequency_distribution(self, text: str) -> dict[str, float]:
        """Calculates normalized word frequencies with Laplace smoothing."""
        words = re.findall(r'\w+', text.lower())
        if not words:
            return {}
        
        counter = Counter(words)
        total = sum(counter.values())
        vocab_size = len(counter)
        
        # Laplace smoothing factor
        alpha = 0.1
        smoothed_total = total + (alpha * vocab_size)
        
        dist = {}
        for word, count in counter.items():
            dist[word] = (count + alpha) / smoothed_total
            
        return dist

    def calculate_entropy(self, text: str) -> float:
        """
        H(n) = - Σ p(t) log2 p(t)
        Calculates Shannon Entropy based on term frequencies.
        """
        dist = self._get_frequency_distribution(text)
        if not dist:
            return 0.0
            
        entropy = -sum(p * math.log2(p) for p in dist.values())
        return float(entropy)

    def kolmogorov_approx(self, text: str) -> float:
        """
        Approximates algorithmic complexity via zlib compression.
        """
        if not text:
            return 0.0
        compressed = zlib.compress(text.encode('utf-8'), level=9)
        return float(len(compressed))

    def kl_divergence(self, text_a: str, text_b: str) -> float:
        """
        D_KL(P || Q) = Σ P(i) log2(P(i) / Q(i))
        Symmetric KL Divergence approximation: (D_KL(P||Q) + D_KL(Q||P)) / 2
        """
        words_a = re.findall(r'\w+', text_a.lower())
        words_b = re.findall(r'\w+', text_b.lower())
        
        if not words_a or not words_b:
            return float('inf') # Maximum divergence if one is empty
            
        counter_a = Counter(words_a)
        counter_b = Counter(words_b)
        
        vocab = set(counter_a.keys()).union(set(counter_b.keys()))
        
        alpha = 0.1 # Laplace smoothing to prevent log(0)
        total_a = sum(counter_a.values()) + alpha * len(vocab)
        total_b = sum(counter_b.values()) + alpha * len(vocab)
        
        d_kl_pq = 0.0
        d_kl_qp = 0.0
        
        for word in vocab:
            p = (counter_a.get(word, 0) + alpha) / total_a
            q = (counter_b.get(word, 0) + alpha) / total_b
            
            d_kl_pq += p * math.log2(p / q)
            d_kl_qp += q * math.log2(q / p)
            
        # Symmetric KL
        return (d_kl_pq + d_kl_qp) / 2.0

    def check_eligibility(self, text_a: str, text_b: str, mass_a: float, mass_b: float) -> bool:
        """
        Eligibility: D_KL < 0.05 AND |mass_a - mass_b| < 0.1
        """
        d_kl = self.kl_divergence(text_a, text_b)
        mass_diff = abs(mass_a - mass_b)
        
        return d_kl < self.KL_DIVERGENCE_THRESHOLD and mass_diff < self.MASS_DIFFERENCE_THRESHOLD

    def evaluate_collapse(self, text_a: str, text_b: str, mass_a: float, mass_b: float) -> CollapseVerdict:
        """
        Evaluates structural collapse of node B into node A.
        Enforces Invariants:
        - I4: Post-collapse entropy >= min(H_a, H_b)
        - I5: Post-collapse mass <= MAX_KINETIC_MULTIPLIER
        - I6: Orthogonal nodes never collapse (D_KL >= 0.05)
        """
        # I6: Orthogonal nodes
        d_kl = self.kl_divergence(text_a, text_b)
        if d_kl >= self.KL_DIVERGENCE_THRESHOLD:
            return CollapseVerdict(False, f"I6 Violation: Nodes are orthogonal (D_KL = {d_kl:.4f} >= {self.KL_DIVERGENCE_THRESHOLD})", mass_a, 0.0)
            
        # Basic eligibility (mass difference)
        if abs(mass_a - mass_b) >= self.MASS_DIFFERENCE_THRESHOLD:
            return CollapseVerdict(False, "Eligibility Violation: Mass difference too high", mass_a, 0.0)

        # I5: Mass ceiling
        post_collapse_mass = mass_a + (mass_b * 0.5) # Fractional mass absorption physics
        if post_collapse_mass > self.MAX_KINETIC_MULTIPLIER:
            return CollapseVerdict(False, f"I5 Violation: Post-collapse mass ({post_collapse_mass:.2f}) exceeds {self.MAX_KINETIC_MULTIPLIER}", mass_a, 0.0)
            
        # I4: Entropy retention
        h_a = self.calculate_entropy(text_a)
        h_b = self.calculate_entropy(text_b)
        
        combined_text = f"{text_a}\n{text_b}"
        post_collapse_entropy = self.calculate_entropy(combined_text)
        
        min_entropy = min(h_a, h_b)
        if post_collapse_entropy < min_entropy:
            return CollapseVerdict(False, f"I4 Violation: Post-collapse entropy ({post_collapse_entropy:.4f}) < Min({min_entropy:.4f})", mass_a, post_collapse_entropy)
            
        # Kolmogorov compression check
        k_a = self.kolmogorov_approx(text_a)
        k_b = self.kolmogorov_approx(text_b)
        k_ab = self.kolmogorov_approx(combined_text)
        
        compression_ratio = k_ab / (k_a + k_b) if (k_a + k_b) > 0 else 1.0
        
        if compression_ratio > 0.85:
            return CollapseVerdict(False, f"Insufficient Kolmogorov Compression (Ratio: {compression_ratio:.2f})", mass_a, post_collapse_entropy)
            
        return CollapseVerdict(True, "Collapse Approved: All thermodynamic invariants satisfied", post_collapse_mass, post_collapse_entropy)
