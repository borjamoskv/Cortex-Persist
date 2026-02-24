"""CORTEX v7 — HDC Algebraic Operations.

Core operations on bipolar hypervectors (±1, int8):
    - bind(a, b):     Element-wise XOR analogue for bipolar → a * b
    - unbind(c, b):   Inverse of bind → c * b (same as bind for bipolar)
    - bundle(*hvs):   Majority-vote superposition of multiple HVs
    - permute(hv, k): Circular shift by k positions (encodes sequence)
    - cosine_similarity(a, b): Normalized dot product
    - random_bipolar(dim): Generate a random ±1 hypervector

All operations use numpy int8 arrays for memory efficiency:
    10k-dim × int8 = 10 KB per vector (vs 40 KB for float32 dense).
"""

from __future__ import annotations

from typing import Final

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "bind",
    "bundle",
    "cosine_similarity",
    "hamming_similarity",
    "permute",
    "random_bipolar",
    "unbind",
]

# Sovereign constants
DEFAULT_DIM: Final[int] = 8000
HVType = NDArray[np.int8]


def random_bipolar(dim: int = DEFAULT_DIM, *, seed: int | None = None) -> HVType:
    """Generate a random bipolar hypervector (±1).

    Args:
        dim: Dimensionality of the hypervector.
        seed: Optional RNG seed for reproducibility.

    Returns:
        numpy int8 array of shape (dim,) with values in {-1, +1}.
    """
    rng = np.random.default_rng(seed)
    return rng.choice(np.array([-1, 1], dtype=np.int8), size=dim)


def bind(a: HVType, b: HVType) -> HVType:
    """Bind two hypervectors (bipolar multiplication).

    Binding creates an association between concepts.
    The result is quasi-orthogonal to both inputs.

    For bipolar vectors: bind(a, b) = a * b (element-wise).
    Self-inverse: bind(bind(a, b), b) ≈ a.

    Args:
        a: First hypervector.
        b: Second hypervector.

    Returns:
        Bound hypervector (same dimensionality).
    """
    return np.multiply(a, b, dtype=np.int8)


def unbind(composite: HVType, key: HVType) -> HVType:
    """Unbind a key from a composite hypervector.

    For bipolar vectors, unbind is identical to bind
    because multiplication by ±1 is self-inverse.

    Args:
        composite: The bound composite vector.
        key: The key to unbind (recover the other component).

    Returns:
        Recovered hypervector (approximate for bundled composites).
    """
    return bind(composite, key)


def bundle(*hvs: HVType) -> HVType:
    """Bundle multiple hypervectors via majority vote.

    Bundling creates a superposition that is similar to all inputs.
    Uses element-wise majority voting: sign(sum(hvs)).

    For ties (even count, sum=0), randomly breaks to +1 or -1.

    Args:
        *hvs: Two or more hypervectors to bundle.

    Returns:
        Bundled hypervector preserving similarity to all inputs.

    Raises:
        ValueError: If fewer than 2 hypervectors are provided.
    """
    if len(hvs) < 2:
        msg = f"bundle() requires at least 2 hypervectors, got {len(hvs)}"
        raise ValueError(msg)

    summed = np.sum(np.stack(hvs), axis=0, dtype=np.int32)
    result = np.sign(summed).astype(np.int8)

    # Break ties deterministically: zeros become +1
    zeros = result == 0
    if np.any(zeros):
        result[zeros] = 1

    return result


def permute(hv: HVType, k: int = 1) -> HVType:
    """Permute a hypervector by circular shift.

    Encodes sequential/positional information.
    permute(hv, 0) → identity.
    permute(hv, k) is quasi-orthogonal to hv for k ≥ 1.

    Args:
        hv: Hypervector to permute.
        k: Number of positions to shift (can be negative).

    Returns:
        Permuted hypervector.
    """
    return np.roll(hv, k)


def cosine_similarity(a: HVType, b: HVType) -> float:
    """Compute cosine similarity between two hypervectors.

    For bipolar vectors, this simplifies to:
        cos(a, b) = dot(a, b) / dim

    Args:
        a: First hypervector.
        b: Second hypervector.

    Returns:
        Similarity score in [-1.0, +1.0].
    """
    dot = int(np.dot(a.astype(np.int32), b.astype(np.int32)))
    return dot / len(a)


def hamming_similarity(a: HVType, b: HVType) -> float:
    """Compute normalized Hamming similarity (fraction of matching elements).

    Args:
        a: First hypervector.
        b: Second hypervector.

    Returns:
        Similarity score in [0.0, 1.0]. 1.0 = identical.
    """
    matches = int(np.sum(a == b))
    return matches / len(a)
