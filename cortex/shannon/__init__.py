"""CORTEX Shannon Module — Information Theory for Memory Intelligence.

Applies Shannon entropy, KL divergence, mutual information,
conditional entropy, cross-entropy, and redundancy analysis
to measure memory quality, detect imbalance, and guide pruning.
"""

from __future__ import annotations

from cortex.shannon.analyzer import (
    conditional_entropy,
    cross_entropy,
    information_value,
    jensen_shannon_divergence,
    kl_divergence,
    max_entropy,
    mutual_information,
    normalized_entropy,
    redundancy,
    shannon_entropy,
)
from cortex.shannon.report import EntropyReport
from cortex.shannon.scanner import MemoryScanner

__all__ = [
    "EntropyReport",
    "MemoryScanner",
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
