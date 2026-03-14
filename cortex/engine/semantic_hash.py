"""
Semantic Hashing Engine — Vectorial Merkle Bridge (Ω₂ / Ω₃).

Replaces byte-exact SHA-256 hashing with embedding-based semantic fingerprints.
A system that compares meaning instead of characters eliminates false positives
when an LLM paraphrases stored content — the structural condition that causes
traditional Merkle Trees to flag valid memory as "corrupted".

Architecture:
  - Fingerprint: SHA-256 of the quantized embedding vector (deterministic)
  - Distance: Cosine similarity between two fingerprint source embeddings
  - Validation: threshold-based semantic equivalence (default: 0.98)

GPU-native: Uses sentence-transformers ONNX with CUDA auto-detection when available.
Edge-compatible: Falls back to CPU. Fingerprint comparison is O(D) where D=384.
"""

from __future__ import annotations

import hashlib
import logging
import struct
from typing import Any

logger = logging.getLogger("cortex.semantic_hash")

__all__ = [
    "SemanticFingerprint",
    "semantic_fingerprint",
    "semantic_distance",
    "is_semantically_equivalent",
    "cosine_similarity",
]

# Quantization precision for deterministic hashing.
# float32 → 6 decimal places gives ~0.0001% error while ensuring
# identical texts always produce identical fingerprints.
_QUANTIZE_DECIMALS = 6


class SemanticFingerprint:
    """Immutable semantic identity of a text.

    Contains both the deterministic hash (for Merkle Trees) and the
    raw embedding vector (for cosine distance computation).
    """

    __slots__ = ("hash", "embedding", "dimension", "text_preview")

    def __init__(
        self,
        hash: str,
        embedding: list[float],
        dimension: int,
        text_preview: str = "",
    ) -> None:
        self.hash = hash
        self.embedding = embedding
        self.dimension = dimension
        self.text_preview = text_preview

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticFingerprint):
            return NotImplemented
        return self.hash == other.hash

    def __hash__(self) -> int:
        return hash(self.hash)

    def __repr__(self) -> str:
        return f"SemanticFingerprint(hash={self.hash[:16]}..., dim={self.dimension})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "hash": self.hash,
            "embedding": self.embedding,
            "dimension": self.dimension,
            "text_preview": self.text_preview,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SemanticFingerprint:
        return cls(
            hash=data["hash"],
            embedding=data["embedding"],
            dimension=data.get("dimension", len(data["embedding"])),
            text_preview=data.get("text_preview", ""),
        )

    def to_bytes(self) -> bytes:
        """Serialize embedding to compact binary (float32 packed).

        Edge-optimized: 384 dims × 4 bytes = 1,536 bytes.
        """
        return struct.pack(f"<{len(self.embedding)}f", *self.embedding)

    @classmethod
    def from_bytes(
        cls, data: bytes, hash_value: str, dimension: int = 384
    ) -> SemanticFingerprint:
        """Deserialize from binary representation."""
        embedding = list(struct.unpack(f"<{dimension}f", data))
        return cls(hash=hash_value, embedding=embedding, dimension=dimension)


def _quantize_embedding(embedding: list[float]) -> list[float]:
    """Quantize embedding to fixed decimal precision for deterministic hashing."""
    return [round(v, _QUANTIZE_DECIMALS) for v in embedding]


def _hash_quantized(quantized: list[float]) -> str:
    """SHA-256 hash of a quantized embedding vector.

    Uses a compact binary representation (struct pack) instead of JSON
    to minimize hash computation time on edge devices.
    """
    packed = struct.pack(f"<{len(quantized)}f", *quantized)
    return hashlib.sha256(packed).hexdigest()


def semantic_fingerprint(
    text: str,
    embedder: Any | None = None,
) -> SemanticFingerprint:
    """Generate a deterministic semantic fingerprint for text.

    Args:
        text: Input text to fingerprint.
        embedder: Optional LocalEmbedder instance. If None, creates one.

    Returns:
        SemanticFingerprint with hash and embedding vector.

    The fingerprint is deterministic: same text + same model = same hash.
    Different texts with identical meaning will have different hashes
    but very high cosine similarity (>0.98).
    """
    if not text or not text.strip():
        raise ValueError("Cannot fingerprint empty text")

    if embedder is None:
        from cortex.embeddings import LocalEmbedder
        embedder = LocalEmbedder()

    embedding = embedder.embed(text)
    if isinstance(embedding[0], list):
        embedding = embedding[0]

    quantized = _quantize_embedding(embedding)
    hash_value = _hash_quantized(quantized)

    return SemanticFingerprint(
        hash=hash_value,
        embedding=embedding,
        dimension=len(embedding),
        text_preview=text[:100],
    )


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    O(D) where D is the embedding dimension (384).
    No external dependencies — runs on any edge device.

    Returns value in [-1.0, 1.0]. For normalized embeddings (L2-norm=1),
    this simplifies to the dot product.
    """
    if len(vec_a) != len(vec_b):
        raise ValueError(
            f"Vector dimension mismatch: {len(vec_a)} vs {len(vec_b)}"
        )

    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def semantic_distance(fp_a: SemanticFingerprint, fp_b: SemanticFingerprint) -> float:
    """Compute semantic distance between two fingerprints.

    Returns 1.0 - cosine_similarity. Range [0.0, 2.0].
    0.0 = identical meaning, 2.0 = opposite meaning.
    """
    return 1.0 - cosine_similarity(fp_a.embedding, fp_b.embedding)


def is_semantically_equivalent(
    fp_a: SemanticFingerprint,
    fp_b: SemanticFingerprint,
    threshold: float = 0.98,
) -> bool:
    """Check if two fingerprints are semantically equivalent.

    Args:
        fp_a: First fingerprint.
        fp_b: Second fingerprint.
        threshold: Minimum cosine similarity for equivalence (default: 0.98).

    Returns:
        True if cosine similarity >= threshold.

    The threshold of 0.98 eliminates false positives from paraphrasing
    while still detecting genuine hallucinations (e.g., "likes apples"
    vs "likes pears" typically scores < 0.90).
    """
    sim = cosine_similarity(fp_a.embedding, fp_b.embedding)
    return sim >= threshold


def batch_fingerprint(
    texts: list[str],
    embedder: Any | None = None,
) -> list[SemanticFingerprint]:
    """Generate fingerprints for multiple texts in a single batch.

    GPU-native: leverages batch encoding for CUDA acceleration.
    """
    if not texts:
        return []

    if embedder is None:
        from cortex.embeddings import LocalEmbedder
        embedder = LocalEmbedder()

    embeddings = embedder.embed_batch(texts)

    results = []
    for text, embedding in zip(texts, embeddings, strict=True):
        quantized = _quantize_embedding(embedding)
        hash_value = _hash_quantized(quantized)
        results.append(
            SemanticFingerprint(
                hash=hash_value,
                embedding=embedding,
                dimension=len(embedding),
                text_preview=text[:100],
            )
        )

    return results
