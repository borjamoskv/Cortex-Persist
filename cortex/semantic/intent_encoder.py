# [C5-REAL] Exergy-Maximized
import numpy as np

from cortex.interfaces.memory_provider import IntentVector, MemoryProvider


class IntentEncoder:
    """
    Decodes the user's string query into an IntentVector with multi-view stochastic sampling.
    """

    def __init__(self, provider: MemoryProvider):
        self.provider = provider

    def encode(self, query: str) -> IntentVector:
        # 1. Base semantic embedding (Mean)
        semantic_mean = self.provider.embed(query)

        q_lower = query.lower()

        temporal_bias_mean = 0.0
        abstraction_level_mean = 0.5

        # Temporal cues
        if any(
            w in q_lower
            for w in ["ayer", "antes", "después", "pasó", "when", "yesterday", "before"]
        ):
            temporal_bias_mean = 0.8

        # Abstraction cues
        if any(
            w in q_lower
            for w in ["resumen", "arquitectura", "overview", "summary", "cómo funciona"]
        ):
            abstraction_level_mean = 0.9
        elif any(w in q_lower for w in ["error", "bug", "line", "falló", "traceback"]):
            abstraction_level_mean = 0.1

        # Task vector
        task_vector = (
            np.zeros_like(semantic_mean)
            if isinstance(semantic_mean, np.ndarray)
            else [0.0] * len(semantic_mean)
        )

        # 3. Multi-view Intent Sampling (Stochastic variance injection)
        # Instead of deterministic routing, we add semantic noise variance
        if isinstance(semantic_mean, np.ndarray):
            noise = np.random.normal(0, 0.05, semantic_mean.shape)
            semantic_sampled = semantic_mean + noise
            semantic_sampled = semantic_sampled / np.linalg.norm(semantic_sampled)
        else:
            semantic_sampled = semantic_mean

        # Add probabilistic variance to biases (exploration bounding)
        temporal_bias = np.clip(np.random.normal(temporal_bias_mean, 0.15), 0.0, 1.0)
        abstraction_level = np.clip(np.random.normal(abstraction_level_mean, 0.15), 0.0, 1.0)

        return IntentVector(
            semantic_vector=semantic_sampled,
            task_vector=task_vector,
            temporal_bias=float(temporal_bias),
            abstraction_level=float(abstraction_level),
        )
