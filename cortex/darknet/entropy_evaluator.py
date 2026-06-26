# [C4-SIM] Warning: Computationally Fragile
"""
Synthetic Text Detection.

Based on probabilistic calculation of perplexity (token predictability) and burstiness
(variance in sentence length/structure).
Highly susceptible to entropy injection and Adversarial Prompting.
DO NOT USE AS CRYPTOGRAPHIC PROOF in zero-trust environments.
"""

import math


class SyntheticTextDetector:
    def __init__(self, token_frequencies: dict[str, float]):
        self.freqs = token_frequencies

    def calculate_perplexity(self, text: str) -> float:
        """Calculate token predictability. Lower perplexity = more likely synthetic."""
        tokens = text.lower().split()
        if not tokens:
            return float("inf")

        log_prob_sum = 0.0
        for t in tokens:
            prob = self.freqs.get(t, 1e-5)
            log_prob_sum += math.log(prob)

        avg_log_prob = log_prob_sum / len(tokens)
        return math.exp(-avg_log_prob)

    def calculate_burstiness(self, text: str) -> float:
        """Variance in sentence length."""
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        if not sentences:
            return 0.0

        lengths = [len(s.split()) for s in sentences]
        mean_length = sum(lengths) / len(lengths)

        variance = sum((length - mean_length) ** 2 for length in lengths) / len(lengths)
        return variance

    def evaluate(self, text: str) -> dict:
        """Returns probabilistic estimation of synthesis."""
        perplexity = self.calculate_perplexity(text)
        burstiness = self.calculate_burstiness(text)

        # AI generated text typically has low perplexity and low burstiness
        is_synthetic = perplexity < 50.0 and burstiness < 10.0

        return {
            "epistemic_level": "C4-SIM",
            "is_synthetic_guess": is_synthetic,
            "perplexity": perplexity,
            "burstiness": burstiness,
            "warning": "Highly susceptible to adversarial prompting. Not a cryptographic proof.",
        }
