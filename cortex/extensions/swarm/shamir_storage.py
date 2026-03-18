"""
ShamirStorage — ΩΩ-HANDOFF Semana 5-6
Pure-Python Shamir Secret Sharing over GF(256) (no external crypto lib).
Splits sensitive handoff payloads into k-of-n shares for multi-backend
distribution across Arweave + IPFS.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

__all__ = [
    "Share",
    "reconstruct_secret",
    "split_secret",
]

# ---------------------------------------------------------------------------
# GF(256) arithmetic — AES-compatible irreducible polynomial x^8+x^4+x^3+x+1
# ---------------------------------------------------------------------------

_GF_EXP: list[int] = [0] * 512
_GF_LOG: list[int] = [0] * 256

# Build exp/log tables for GF(2^8)
_x = 1
for _i in range(255):
    _GF_EXP[_i] = _x
    _GF_LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11B  # reduce with AES polynomial
for _i in range(255, 512):
    _GF_EXP[_i] = _GF_EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    """GF(256) multiplication via log/exp tables. O(1)."""
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _gf_div(a: int, b: int) -> int:
    """GF(256) division. b must not be zero."""
    if b == 0:
        raise ZeroDivisionError("GF(256) division by zero")
    if a == 0:
        return 0
    return _GF_EXP[(_GF_LOG[a] - _GF_LOG[b]) % 255]


def _evaluate_polynomial(coeffs: list[int], x: int) -> int:
    """Evaluate polynomial with given coefficients at x in GF(256). O(degree)."""
    result = 0
    for coeff in reversed(coeffs):
        result = _gf_mul(result, x) ^ coeff
    return result


def _lagrange_interpolate_at_zero(shares: list[tuple[int, int]]) -> int:
    """Lagrange interpolation at x=0 over GF(256). O(k^2)."""
    result = 0
    for i in range(len(shares)):
        xi, yi = shares[i]
        num = 1
        den = 1
        for j in range(len(shares)):
            if i == j:
                continue
            xj, _ = shares[j]
            num = _gf_mul(num, xj)
            den = _gf_mul(den, xi ^ xj)
        result ^= _gf_mul(_gf_div(num, den), yi)
    return result


# ---------------------------------------------------------------------------
# Domain type
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Share:
    """One Shamir share of a split secret."""

    index: int           # 1-based share index (x-coordinate)
    threshold: int       # k — minimum shares to reconstruct
    n_total: int         # n — total shares produced
    payload_hex: str     # hex-encoded share bytes (one per secret byte)

    @property
    def payload_bytes(self) -> bytes:
        return bytes.fromhex(self.payload_hex)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def split_secret(data: bytes, n: int, k: int) -> list[Share]:
    """Split `data` into `n` Shamir shares, requiring `k` to reconstruct.

    Each byte of `data` is treated as a separate secret; the polynomial
    evaluations are batched, producing one list of share-bytes per share index.

    Args:
        data: Secret bytes to split.
        n:    Total number of shares to produce (2 ≤ k ≤ n ≤ 255).
        k:    Reconstruction threshold (minimum shares needed).

    Returns:
        List of `n` Share objects with 1-based indices [1..n].
    """
    if not (2 <= k <= n <= 255):
        raise ValueError(f"Invalid (n={n}, k={k}): require 2 ≤ k ≤ n ≤ 255")
    if not data:
        raise ValueError("Secret must be non-empty")

    shares_bytes: list[list[int]] = [[] for _ in range(n)]

    for byte_val in data:
        # Random polynomial of degree k-1: coeffs[0] = secret, rest random
        coeffs = [byte_val] + [secrets.randbelow(256) for _ in range(k - 1)]
        for idx in range(n):
            x = idx + 1  # x-coordinates are [1..n], never 0
            shares_bytes[idx].append(_evaluate_polynomial(coeffs, x))

    return [
        Share(
            index=idx + 1,
            threshold=k,
            n_total=n,
            payload_hex=bytes(share_data).hex(),
        )
        for idx, share_data in enumerate(shares_bytes)
    ]


def reconstruct_secret(shares: list[Share]) -> bytes:
    """Reconstruct the secret from at least `k` shares.

    Args:
        shares: At least `threshold` Share objects from the same split.

    Returns:
        Original secret bytes.

    Raises:
        ValueError: If fewer than `threshold` shares provided or shares mismatch.
    """
    if not shares:
        raise ValueError("No shares provided")

    k = shares[0].threshold
    if len(shares) < k:
        raise ValueError(
            f"Need at least {k} shares to reconstruct, got {len(shares)}"
        )

    # Validate consistency
    n_bytes = len(shares[0].payload_bytes)
    if any(len(s.payload_bytes) != n_bytes for s in shares):
        raise ValueError("All shares must have the same payload length")

    # Use exactly k shares (first k if more provided)
    active = shares[:k]
    result = bytearray()

    for byte_idx in range(n_bytes):
        points = [(s.index, s.payload_bytes[byte_idx]) for s in active]
        result.append(_lagrange_interpolate_at_zero(points))

    return bytes(result)


# ---------------------------------------------------------------------------
# Convenience: secure random bytes (re-exported for callers)
# ---------------------------------------------------------------------------

def random_key(length: int = 32) -> bytes:
    """Generate cryptographically secure random bytes."""
    return os.urandom(length)
