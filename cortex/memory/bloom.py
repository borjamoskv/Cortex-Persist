"""CORTEX v6+ — Bloom Filter for O(1) Fast-Negative Dedup Check.

Strategy #8: Before computing expensive embeddings and running
the ART Gate, a Bloom filter answers in O(1):
"Does something similar to this fact PROBABLY exist?"

- If NO  → store directly, skip ART Gate (saves ~10ms per store)
- If YES → run full ART Gate pipeline

Uses content hashing with multiple hash functions for low
false positive rates (~1% at 10 bits per element).
"""

from __future__ import annotations

import hashlib
import math


class BloomFilter:
    """Space-efficient probabilistic set membership test.

    Uses k independent hash functions over an m-bit array.
    False positives possible, false negatives impossible.
    """

    __slots__ = ("_bits", "_k", "_m")

    def __init__(self, expected_items: int = 10_000, fp_rate: float = 0.01):
        """Initialize with expected number of items and desired FP rate.

        Args:
            expected_items: Expected number of items to insert.
            fp_rate: Desired false positive rate (0.01 = 1%).
        """
        if expected_items <= 0:
            expected_items = 1
        if fp_rate <= 0 or fp_rate >= 1:
            fp_rate = 0.01

        # Optimal bit array size: m = -n*ln(p) / (ln2)^2
        self._m = max(
            64,
            int(-expected_items * math.log(fp_rate) / (math.log(2) ** 2)),
        )
        # Optimal number of hash functions: k = (m/n) * ln2
        self._k = max(
            1,
            int((self._m / expected_items) * math.log(2)),
        )
        self._bits = bytearray(self._m // 8 + 1)

    def _hashes(self, item: str) -> list[int]:
        """Generate k hash positions using double hashing."""
        h1 = int(hashlib.md5(item.encode(), usedforsecurity=False).hexdigest(), 16)
        h2 = int(hashlib.sha1(item.encode(), usedforsecurity=False).hexdigest(), 16)
        return [(h1 + i * h2) % self._m for i in range(self._k)]

    def add(self, item: str) -> None:
        """Add an item to the filter."""
        for pos in self._hashes(item):
            byte_idx, bit_idx = divmod(pos, 8)
            self._bits[byte_idx] |= 1 << bit_idx

    def might_contain(self, item: str) -> bool:
        """Check if item MIGHT exist (false positives possible)."""
        return all(self._bits[pos // 8] & (1 << (pos % 8)) for pos in self._hashes(item))

    @property
    def size_bytes(self) -> int:
        """Memory footprint of the filter."""
        return len(self._bits)

    @property
    def hash_count(self) -> int:
        """Number of hash functions used."""
        return self._k

    @property
    def bit_count(self) -> int:
        """Size of the bit array."""
        return self._m
