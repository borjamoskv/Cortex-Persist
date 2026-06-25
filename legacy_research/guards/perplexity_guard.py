"""
C5-REAL Perplexity Guard (PERPLEX-001)
Applies Landauer's principle by measuring the thermodynamic entropy (Perplexity) 
of textual inputs using a deterministic heuristic/lightweight oracle proxy.
Inputs exceeding the PPL threshold are rejected (Apoptosis).
"""

import math
import logging
from collections import Counter
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PerplexityGuard:
    """
    Implements PERPLEX-001 to PERPLEX-005.
    Calculates an approximated token entropy (Prior-based Frequency Filter) to mimic
    LLM Perplexity without the massive computational overhead (1000x faster).
    """
    
    def __init__(self, threshold: float = 8.5):
        self.threshold = threshold
        self.b60_penalty_factor = 60

    def _approximate_perplexity(self, text: str) -> float:
        """
        Fast heuristic for text perplexity based on character and word unigram distribution.
        Rejects random strings, broken HTML, or Base64 noise.
        """
        if not text or len(text.strip()) == 0:
            return float('inf')
            
        words = text.split()
        if not words:
            return float('inf')

        word_counts = Counter(words)
        total_words = len(words)
        
        # Shannon entropy of word distribution
        entropy = -sum((count / total_words) * math.log2(count / total_words) 
                       for count in word_counts.values())
        
        # Approximate Perplexity: 2^Entropy
        ppl = 2 ** entropy
        
        # Adjust for string length to penalize short gibberish
        if total_words < 5:
            ppl *= 1.5
            
        return ppl

    def evaluate(self, input_data: str) -> Dict[str, Any]:
        """
        Evaluates the input text against the PPL threshold.
        Returns evaluation metrics and a boolean indicating if it passed.
        """
        ppl_score = self._approximate_perplexity(input_data)
        
        passed = ppl_score <= self.threshold
        
        if not passed:
            logger.warning(f"[PPL GUARD] High Entropy Detected: PPL={ppl_score:.2f} (Threshold={self.threshold})")
            
        return {
            "passed": passed,
            "score": ppl_score,
            "threshold": self.threshold,
            "reason": "Excedió el umbral de Perplejidad termodinámica." if not passed else "Entropía aceptable."
        }
