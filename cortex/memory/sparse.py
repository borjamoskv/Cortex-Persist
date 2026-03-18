"""CORTEX v6+ — Sparse Encoding (Mushroom Body-inspired).

Strategy 3: Implements dimensionality expansion and sparse activation
inspired by the Drosophila Mushroom Body circuit.

The biological circuit:
  50 Projection Neurons → 2000 Kenyon Cells (40x expansion)
  APL neuron provides global inhibition → only ~5% KC active per odor

Computational translation:
  768-dim embedding → 3072-dim sparse representation
  Global inhibition via top-k selection → only top 5% survive
  Result: near-zero interference between engram memories.
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger("cortex.memory.sparse")


class MushroomBodyEncoder:
    """Sparse encoder inspired by Drosophila Mushroom Body.

    Expands input embeddings into a higher-dimensional space with
    sparse activation, dramatically reducing inter-memory interference.
    """

    def __init__(
        self,
        expansion_factor: int = 4,
        sparsity: float = 0.05,
        seed: int = 42,
    ):
        self._expansion = expansion_factor
        self._sparsity = sparsity
        self._seed = seed
        self._projection: list[list[float]] | None = None

    def _init_projection(self, input_dim: int) -> list[list[float]]:
        """Initialize random projection matrix (PN → KC mapping).

        Uses deterministic pseudo-random for reproducibility.
        """
        import random

        rng = random.Random(self._seed)
        output_dim = input_dim * self._expansion
        # Xavier-like initialization
        scale = math.sqrt(2.0 / (input_dim + output_dim))
        return [[rng.gauss(0, scale) for _ in range(input_dim)] for _ in range(output_dim)]

    def encode(self, embedding: list[float]) -> list[float]:
        """Expand and sparsify an embedding.

        1. Project to higher dimension (PN → KC expansion)
        2. Apply APL global inhibition (top-k sparsity)
        """
        input_dim = len(embedding)
        if input_dim == 0:
            return []

        # Lazy init projection matrix
        if self._projection is None or len(self._projection[0]) != input_dim:
            self._projection = self._init_projection(input_dim)

        output_dim = input_dim * self._expansion

        # Matrix-vector multiply (expansion)
        expanded = [
            sum(w * x for w, x in zip(row, embedding, strict=True)) for row in self._projection
        ]

        # ReLU activation
        expanded = [max(0.0, v) for v in expanded]

        # APL Global Inhibition: keep only top k% active
        k = max(1, int(output_dim * self._sparsity))
        if k < output_dim:
            # Find k-th largest value
            sorted_vals = sorted(expanded, reverse=True)
            threshold = sorted_vals[k - 1] if k <= len(sorted_vals) else 0.0

            # Zero out everything below threshold
            expanded = [v if v >= threshold else 0.0 for v in expanded]

        # L2 normalize the sparse vector
        norm = math.sqrt(sum(v * v for v in expanded))
        if norm > 0:
            expanded = [v / norm for v in expanded]

        return expanded

    def compute_sparsity_ratio(self, sparse_vec: list[float]) -> float:
        """Compute actual sparsity of an encoded vector."""
        if not sparse_vec:
            return 1.0
        active = sum(1 for v in sparse_vec if v > 0.0)
        return 1.0 - (active / len(sparse_vec))
