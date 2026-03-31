"""
CORTEX — VOID-VEC (Void-Bit) Engine.

Sovereign 1-bit Binary Quantization and bitwise similarity logic.
Achieves O(1) Hamming Distance comparison via bit-packing and POPCOUNT.
Reduced exergy footprint for the Legion 10,000 swarm.
"""

from __future__ import annotations

import numpy as np

__all__ = ["pack_void_bit", "void_hamming_dist", "void_similarity", "unpack_void_bit"]


def pack_void_bit(vector: list[float] | np.ndarray) -> bytes:
    """
    Transforms float32/int8 vector into 1-bit packed binary representation.

    Logic: Sign(x) -> 1 if x > 0 else 0.
    Packs 8 dimensions into 1 byte.
    """
    arr = np.array(vector, dtype=np.float32)
    # Threshold at zero (Sign bit extraction)
    binary = (arr > 0).astype(np.uint8)

    # Pack bits into bytes
    # Ensure dimension is multiple of 8 (CORTEX dimensions are usually 768, 1024, or 1536)
    dim = len(binary)
    if dim % 8 != 0:
        # Pad with zeros to 8-bit boundary
        padding = 8 - (dim % 8)
        binary = np.pad(binary, (0, padding), "constant")

    # Efficient packing using bit manipulation
    packed = np.packbits(binary)
    return packed.tobytes()


def void_hamming_dist(a: bytes, b: bytes) -> int:
    """
    Calculates the Hamming Distance between two bit-packed vectors.
    Uses Python 3.10+ int.bit_count() for hardware-level POPCOUNT.
    """
    # Convert bytes to big integers for fast bitwise XOR
    int_a = int.from_bytes(a, byteorder="big")
    int_b = int.from_bytes(b, byteorder="big")

    # Hamming distance is the number of set bits in (a XOR b)
    # Lower distance = Higher similarity
    return (int_a ^ int_b).bit_count()


def void_similarity(a: bytes, b: bytes, total_dim: int) -> float:
    """
    Calculates Normalized Hamming Similarity [0.0, 1.0].

    Eq: 1.0 - (Hamming_Dist / Total_Bits)
    """
    dist = void_hamming_dist(a, b)
    return 1.0 - (dist / total_dim)


def unpack_void_bit(packed: bytes, dim: int) -> np.ndarray:
    """Explodes bits back into float32 [-1, 1] (Structural Loss Warning)."""
    binary = np.unpackbits(np.frombuffer(packed, dtype=np.uint8))
    # Slice to original dimension
    binary = binary[:dim]
    return (binary.astype(np.float32) * 2.0) - 1.0
