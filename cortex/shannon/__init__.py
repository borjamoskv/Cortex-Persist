"""CORTEX Shannon Module — Information Theory for Memory Intelligence.

Applies Shannon entropy, KL divergence, mutual information,
conditional entropy, cross-entropy, redundancy analysis,
and exergy scoring to measure memory quality, detect imbalance,
quantify useful work, and guide pruning.

Status: IMPLEMENTED (Ω₁₃ enforcement — exergy wired into hot paths).
"""

from __future__ import annotations

from cortex.shannon.analyzer import (
    conditional_entropy,
    cross_entropy,
    dead_weight,
    exergy_ratio,
    exergy_score,
    information_value,
    jensen_shannon_divergence,
    kl_divergence,
    max_entropy,
    mutual_information,
    normalized_entropy,
    redundancy,
    shannon_entropy,
)
from cortex.shannon.exergy import ExergyReport, compute_exergy_report
from cortex.shannon.immortality import ImmortalityIndex
from cortex.shannon.report import EntropyReport
from cortex.shannon.scanner import MemoryScanner

__all__ = [
    "EntropyReport",
    "ExergyReport",
    "ImmortalityIndex",
    "MemoryScanner",
    "compute_exergy_report",
    "conditional_entropy",
    "cross_entropy",
    "dead_weight",
    "exergy_ratio",
    "exergy_score",
    "information_value",
    "jensen_shannon_divergence",
    "kl_divergence",
    "max_entropy",
    "mutual_information",
    "normalized_entropy",
    "redundancy",
    "shannon_entropy",
]
