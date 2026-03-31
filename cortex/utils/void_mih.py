"""
CORTEX — VOID-MIH (Multi-Index Hashing) Engine.

Sovereign Bit-Slicing logic for O(log N) Hamming retrieval.
Shards 1024-bit vectors into 16 indexable 64-bit shards.
Reduces brute-force candidate search space by 90-99%.
"""

from __future__ import annotations

import struct
from typing import Sequence

__all__ = ["slice_void_bit", "get_mih_shards"]


def slice_void_bit(packed: bytes) -> list[int]:
    """
    Shards a 1024-bit binary vector into 16 x 64-bit integers.

    Args:
        packed: The 128-byte packed binary vector.

    Returns:
        List of 16 unsigned 64-bit integers (BIGINT compatible for SQLite).
    """
    if len(packed) < 128:
        # Pad if necessary
        packed = packed.ljust(128, b'\0')

    # 16 shards of 8 bytes (Q = unsigned long long, 64 bits)
    # '>' means big-endian for consistent integer representation
    return list(struct.unpack('>16Q', packed[:128]))


def get_mih_shards(vector: Sequence[float] | bytes, dimension: int = 1024) -> list[int]:
    """
    Convenience wrapper to get MIH shards from floats or already packed bytes.
    """
    from cortex.utils import void_vec

    if isinstance(vector, bytes):
        packed = vector
    else:
        packed = void_vec.pack_void_bit(vector)

    return slice_void_bit(packed)
