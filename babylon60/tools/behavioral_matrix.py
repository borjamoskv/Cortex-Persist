#!/usr/bin/env python3
"""
BABYLON-60 / CORTEX: behavioral_matrix.py
Sovereign Black-Box Behavioral Signature Engine

Enforces evaluation of model behavior along dimensions 9 to 16:
- Conversational Curvature
- Conceptual Elasticity
- Perturbation Robustness
- Compression Fingerprint
- Expansion Footprint
- Contradiction Management
- Minimal Inference Profile
- Metacognitive Coherence
"""

import os
import sys
import json
import hashlib
import statistics
import math
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

@dataclass
class ConversationTurn:
    prompt: str
    response: str
    latency_ms: float
    completion_tokens: int

class BehavioralAnalyzer:
    """
    Computes mathematical invariants over prompt-response sets to isolate
    behavioral footprints without relying on model-labeled classes.
    """
    def __init__(self, embedding_provider=None):
        self.embedding_provider = embedding_provider

    def _get_embedding(self, text: str) -> np.ndarray:
        if self.embedding_provider:
            return np.array(self.embedding_provider(text))
        # Fallback determinista simple si no hay embedding model en local
        # Basado en hashing acumulativo para no romper la ejecución de pruebas
        h = hashlib.sha256(text.encode("utf-8")).digest()
        return np.array([float(b) for b in h]) / 255.0

    def compute_shannon_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        words = re.findall(r"\w+", text.lower())
        if not words:
            return 0.0
        counts = {}
        for w in words:
            counts[w] = counts.get(w, 0) + 1
        total = len(words)
        return -sum((count / total) * math.log2(count / total) for count in counts.values())

    def analyze_curvature(self, history: List[ConversationTurn]) -> float:
        """
        Dimension 9: Measures response drift over a multi-turn conversation.
        Low values represent high context stickiness (reusing exact semantic vectors).
        """
        if len(history) < 2:
            return 0.0
        similarities = []
        for i in range(1, len(history)):
            v_prev = self._get_embedding(history[i-1].response)
            v_curr = self._get_embedding(history[i].response)
            dot = np.dot(v_prev, v_curr)
            norm_p = np.linalg.norm(v_prev)
            norm_c = np.linalg.norm(v_curr)
            sim = dot / (norm_p * norm_c) if norm_p > 0 and norm_c > 0 else 0.0
            similarities.append(sim)
        return float(statistics.mean(similarities))

    def analyze_elasticity(self, variants: List[str]) -> float:
        """
        Dimension 10: Measures invariant conceptual mapping across multiple formats.
        Computes variance over the embedding space. Lower is more invariant.
        """
        if not variants:
            return 0.0
        embeds = [self._get_embedding(v) for v in variants]
        matrix = np.array(embeds)
        # Compute trace of the covariance matrix
        cov = np.cov(matrix)
        if cov.ndim == 0:
            return 0.0
        return float(np.trace(cov))

    def analyze_robustness(self, original: str, perturbed: List[str]) -> float:
        """
        Dimension 11: Measures delta of response variance over small prompt mutations.
        """
        if not perturbed:
            return 1.0
        v_orig = self._get_embedding(original)
        deltas = []
        for p in perturbed:
            v_p = self._get_embedding(p)
            dot = np.dot(v_orig, v_p)
            norm_o = np.linalg.norm(v_orig)
            norm_p = np.linalg.norm(v_p)
            sim = dot / (norm_o * norm_p) if norm_o > 0 and norm_p > 0 else 0.0
            deltas.append(1.0 - sim)
        return float(statistics.mean(deltas))

    def analyze_compression(self, sequence: List[str]) -> List[float]:
        """
        Dimension 12: Sequence of Shannon entropy drops.
        Expects a sequence representing: Original -> 80% -> 50% -> 20% -> 1-Sentence -> 3-Words
        """
        return [self.compute_shannon_entropy(step) for step in sequence]

    def analyze_expansion(self, sequence: List[str]) -> List[float]:
        """
        Dimension 13: Unique word growth rate over progressive expansions.
        """
        growth_rates = []
        for step in sequence:
            words = re.findall(r"\w+", step.lower())
            unique = len(set(words))
            total = len(words)
            growth_rates.append(unique / max(total, 1))
        return growth_rates

    def classify_contradiction(self, final_response: str) -> str:
        """
        Dimension 14: Determines strategy against chronologically distributed conflicts.
        Uses simple heuristic mapping on response structure.
        """
        text = final_response.lower()
        if "contradict" in text or "conflict" in text or "inconsist" in text:
            return "Conflict Assert"
        if "but" in text or "however" in text or "reconcil" in text:
            return "Reconciliation Attempt"
        # Fallback to bias patterns
        return "Narrative Absorption / Ignored"

    def classify_minimal_inference(self, response: str) -> str:
        """
        Dimension 15: Discovers implicit bias type under sub-determined facts.
        """
        text = response.lower()
        if "rain" in text or "weather" in text or "shower" in text:
            return "Naturalistic Bias (Physics)"
        if "push" in text or "river" in text or "someone" in text:
            return "Social Adversarial Bias"
        return "Unspecified / Alternate"

    def analyze_metacognitive_coherence(self, original: str, corrected: str) -> float:
        """
        Dimension 16: Shift of confidence vector after negative feedback.
        Returns the cosine distance between the pre and post critique responses.
        """
        v_orig = self._get_embedding(original)
        v_corr = self._get_embedding(corrected)
        dot = np.dot(v_orig, v_corr)
        norm_o = np.linalg.norm(v_orig)
        norm_c = np.linalg.norm(v_corr)
        sim = dot / (norm_o * norm_c) if norm_o > 0 and norm_c > 0 else 0.0
        return float(1.0 - sim)

def compute_mahalanobis_distance(u: np.ndarray, v: np.ndarray, cov: np.ndarray) -> float:
    """
    Computes Mahalanobis distance across the behavioral vector space.
    """
    delta = u - v
    try:
        inv_cov = np.linalg.inv(cov)
        return float(math.sqrt(np.dot(np.dot(delta, inv_cov), delta)))
    except np.linalg.LinAlgError:
        # Fallback to Euclidean if covariance is singular
        return float(np.linalg.norm(delta))
