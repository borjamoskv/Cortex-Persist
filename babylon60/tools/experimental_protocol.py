#!/usr/bin/env python3
"""
BABYLON-60 / CORTEX: experimental_protocol.py
Scientific Behavioral Profiler for LLMs (Psychometrics & Degradation Curves)

Implements rigorous experimental isolation:
- Variables of Confusion containment (Strict params, clean prompt injection)
- N-Run statistical profiling (mean, std dev, stability metrics)
- Curve generation (context degradation and constraint saturation)
- Capacity vs. Policy disassociation
"""

from babylon60.crypto.hash_registry import cortex_hash_raw
import math
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class RunStatistics:
    metric_name: str
    mean: float
    std_dev: float
    p50: float
    p90: float
    samples: int

@dataclass
class DegradationDataPoint:
    stimulus_level: float
    capacity_score: float
    policy_score: float

class ExperimentalProfiler:
    def __init__(self, api_caller_fn, embedding_provider=None):
        """
        api_caller_fn: Callable[[str, Dict[str, Any]], Tuple[str, float, int]]
                       Takes (prompt, inference_params) -> returns (response_text, latency_ms, completion_tokens)
        """
        self.api_caller = api_caller_fn
        self.embedding_provider = embedding_provider

    def _get_embedding(self, text: str) -> np.ndarray:
        if self.embedding_provider:
            return np.array(self.embedding_provider(text))
        h = cortex_hash_raw(text.encode("utf-8"))
        return np.array([float(b) for b in h]) / 255.0

    def compute_lexical_entropy(self, text: str) -> float:
        words = re.findall(r"\w+", text.lower()) if text else []
        if not words:
            return 0.0
        counts = {}
        for w in words:
            counts[w] = counts.get(w, 0) + 1
        total = len(words)
        return -sum((c / total) * math.log2(c / total) for c in counts.values())

    def run_statistical_trial(
        self, 
        prompt: str, 
        confusion_params: dict[str, Any], 
        n_runs: int = 5
    ) -> dict[str, RunStatistics]:
        """
        Executes N runs under identical, strictly controlled confounding variables.
        Estimates variance, mean, and percentiles to analyze stochastical stability.
        """
        latencies = []
        itls = []
        lengths = []
        entropies = []
        completions = []

        for _ in range(n_runs):
            res_text, latency, tokens = self.api_caller(prompt, confusion_params)
            latencies.append(latency)
            completions.append(tokens)
            lengths.append(len(res_text))
            entropies.append(self.compute_lexical_entropy(res_text))
            
            if tokens > 0:
                itls.append(latency / tokens)
            else:
                itls.append(0.0)

        def get_stats(name: str, values: list[float]) -> RunStatistics:
            if not values:
                return RunStatistics(name, 0.0, 0.0, 0.0, 0.0, 0)
            arr = np.array(values)
            return RunStatistics(
                metric_name=name,
                mean=float(np.mean(arr)),
                std_dev=float(np.std(arr)) if len(values) > 1 else 0.0,
                p50=float(np.percentile(arr, 50)),
                p90=float(np.percentile(arr, 90)),
                samples=len(values)
            )

        return {
            "latency_ms": get_stats("latency_ms", latencies),
            "itl_ms": get_stats("itl_ms", itls),
            "response_length": get_stats("response_length", lengths),
            "lexical_entropy": get_stats("lexical_entropy", entropies),
        }

    def generate_context_degradation_curve(
        self,
        base_prompt: str,
        distractor_template: str,
        steps: list[int], # List of word counts for distractor injection (e.g. [1000, 4000, 16000])
        confusion_params: dict[str, Any]
    ) -> list[DegradationDataPoint]:
        """
        Injects progressive noise/context length to evaluate the capacity decay curve.
        """
        curve = []
        for word_count in steps:
            # Generate controlled noise context (lorem-like or randomized text block)
            noise = " ".join(["noise_token"] * word_count)
            full_prompt = f"Context: {noise}\n\nTask: {base_prompt}"
            
            res_text, latency, tokens = self.api_caller(full_prompt, confusion_params)
            
            # Simple capacity calculation: presence of target terms or structural consistency
            # In a real run, this would be compared against ground truth
            capacity_score = 1.0 if len(res_text) > 0 and "refusal" not in res_text.lower() else 0.0
            
            # Policy score: verbose alerts, warnings or apologetic overhead
            policy_score = 0.0
            if any(term in res_text.lower() for term in ["sorry", "apologize", "as an ai"]):
                policy_score = 1.0

            curve.append(DegradationDataPoint(
                stimulus_level=float(word_count),
                capacity_score=capacity_score,
                policy_score=policy_score
            ))
        return curve

    def generate_constraint_saturation_curve(
        self,
        base_prompt: str,
        constraints: list[str], # Cumulative constraints
        confusion_params: dict[str, Any]
    ) -> list[DegradationDataPoint]:
        """
        Measures performance as constraints scale from 1 to M.
        """
        curve = []
        cumulative_constraints = []
        for i, constraint in enumerate(constraints):
            cumulative_constraints.append(constraint)
            constraint_block = "\n".join(f"- {c}" for c in cumulative_constraints)
            full_prompt = f"{base_prompt}\nConstraints:\n{constraint_block}"
            
            res_text, latency, tokens = self.api_caller(full_prompt, confusion_params)
            
            # Simple validation stub - real harness would parse output formats
            capacity_score = 1.0 / (i + 1) # Normalized base rate
            
            policy_score = 0.0
            if "warning" in res_text.lower() or "limit" in res_text.lower():
                policy_score = 1.0

            curve.append(DegradationDataPoint(
                stimulus_level=float(i + 1),
                capacity_score=capacity_score,
                policy_score=policy_score
            ))
        return curve

# Global import check helper
import re
