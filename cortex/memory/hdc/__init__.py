"""CORTEX v7 — Hyperdimensional Computing Memory Engine.

Sovereign semantic memory using algebraic hypervectors (10k-dim bipolar ±1).
Replaces dense ML embeddings with composable, traceable, zero-model vector ops.

Architecture:
    - codec.py:       Text → Hypervector encoder (no ML model needed)
    - algebra.py:     Bind ⊗, Bundle +, Permute Π, Unbind, Similarity
    - item_memory.py: Codebook of atomic symbols → random hypervectors
    - store.py:       HDCVectorStoreL2 with recall + decomposition

Opt-in via CORTEX_HDC=1 environment variable.
"""

from __future__ import annotations

from cortex.memory.hdc.algebra import (
    bind,
    bundle,
    cosine_similarity,
    permute,
    random_bipolar,
    unbind,
)
from cortex.memory.hdc.codec import HDCEncoder
from cortex.memory.hdc.item_memory import ItemMemory
from cortex.memory.hdc.store import HDCVectorStoreL2

__all__ = [
    "HDCEncoder",
    "HDCVectorStoreL2",
    "ItemMemory",
    "bind",
    "bundle",
    "cosine_similarity",
    "permute",
    "random_bipolar",
    "unbind",
]
