# [C5-REAL] Exergy-Maximized
"""Canonical Hash Construction.

Provides deterministic JSON serialization and null-byte separated
hash computation for the transaction ledger. Hardens against
preimage and collision attacks on the hash chain.

Hash Scheme Versions:
    v1: colon-delimited   f"{prev}:{project}:{action}:{detail}:{ts}"
    v2: null-byte canon   f"{prev}\\x00{project}\\x00{action}\\x00{canonical_detail}\\x00{ts}"
    v3: tenant-bound      f"v3\\x00{tenant}\\x00{prev}\\x00{project}\\x00{action}\\x00{canonical_detail}\\x00{ts}"
"""

from __future__ import annotations

import datetime
import hashlib
import json
import time
from typing import Any

__all__ = [
    "canonical_json",
    "compute_fact_hash",
    "compute_tx_hash",
    "compute_tx_hash_v1",
    "now_iso",
]


def now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.datetime.fromtimestamp(time.time(), tz=datetime.timezone.utc).isoformat()


# ─── Canonical JSON ───────────────────────────────────────────────


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, ASCII-safe.

    Guarantees identical output for semantically identical input
    regardless of Python dict insertion order.

    Args:
        obj: Any JSON-serializable object.

    Returns:
        Canonical JSON string.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


# ─── Transaction Hash ────────────────────────────────────────────

HASH_VERSION = 3


def compute_tx_hash(
    prev_hash: str,
    project: str,
    action: str,
    detail_json: str,
    timestamp: str,
    tenant_id: str | None = None,
) -> str:
    """Compute transaction hash using null-byte separated canonical form.

    Uses \\x00 (null byte) as field separator to prevent boundary
    confusion when fields contain colons or other delimiters. New
    tenant-scoped writes should pass ``tenant_id`` so the digest cannot be
    transplanted into another tenant chain while retaining the same hash.

    Args:
        prev_hash: Hash of the previous transaction, or "GENESIS".
        project: Project identifier.
        action: Transaction action (store, deprecate, vote, etc.).
        detail_json: Canonical JSON string of transaction detail.
        timestamp: ISO 8601 UTC timestamp.
        tenant_id: Optional tenant binding for v3 hashes. Omit only when
            creating or verifying legacy v2 transactions.

    Returns:
        SHA-256 hex digest of the canonical input.
    """
    if tenant_id is None:
        h_input = f"{prev_hash}\x00{project}\x00{action}\x00{detail_json}\x00{timestamp}"
    else:
        h_input = (
            f"v3\x00{tenant_id}\x00{prev_hash}\x00{project}"
            f"\x00{action}\x00{detail_json}\x00{timestamp}"
        )
    return hashlib.sha256(h_input.encode("utf-8")).hexdigest()


def compute_tx_hash_v1(
    prev_hash: str,
    project: str,
    action: str,
    detail_json: str,
    timestamp: str,
) -> str:
    """Legacy v1 hash: colon-delimited concatenation.

    Kept for backward-compatible verification of transactions
    created before the canonical hash migration.
    """
    h_input = f"{prev_hash}:{project}:{action}:{detail_json}:{timestamp}"
    return hashlib.sha256(h_input.encode("utf-8")).hexdigest()


def compute_fact_hash(content: str) -> str:
    """Compute deterministic SHA-256 hash for fact content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
