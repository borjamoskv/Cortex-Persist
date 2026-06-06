# [C5-REAL] Exergy-Maximized
"""CORTEX Shannon Module - Information Theory for Memory Intelligence.

Applies Shannon entropy, KL divergence, mutual information,
conditional entropy, cross-entropy, redundancy analysis,
exergy scoring, and Exergetic Epistemology (ΞΕ) frontier primitives
to measure memory quality, detect imbalance, quantify useful work,
audit cryptographic security, and guide pruning.

Status: IMPLEMENTED (Ω₁₃ enforcement - exergy wired into hot paths).
ΞΕ Status: epistemology.py - Rényi, entropy rate, compression proxy,
           DPI verification, free energy guard, Φ proxy.
"""

from __future__ import annotations

from cortex.extensions.shannon.analyzer import (
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
from cortex.extensions.shannon.epistemology import (
    assembly_index_proxy,
    compression_intelligence,
    dpi_verify,
    entropy_rate,
    free_energy_divergence,
    min_entropy,
    phi_proxy,
    renyi_entropy,
)
from cortex.extensions.shannon.exergy import ExergyReport, compute_exergy_report
from cortex.extensions.shannon.immortality import ImmortalityIndex
from cortex.extensions.shannon.report import EntropyReport
from cortex.extensions.shannon.scanner import MemoryScanner

__all__ = [
    "EntropyReport",
    "ExergyReport",
    "ImmortalityIndex",
    "MemoryScanner",
    "assembly_index_proxy",
    "compression_intelligence",
    "compute_exergy_report",
    "conditional_entropy",
    "cross_entropy",
    "dead_weight",
    "dpi_verify",
    "entropy_rate",
    "exergy_ratio",
    "exergy_score",
    "free_energy_divergence",
    "information_value",
    "jensen_shannon_divergence",
    "kl_divergence",
    "max_entropy",
    "min_entropy",
    "mutual_information",
    "normalized_entropy",
    "phi_proxy",
    "redundancy",
    "renyi_entropy",
    "shannon_entropy",
]
