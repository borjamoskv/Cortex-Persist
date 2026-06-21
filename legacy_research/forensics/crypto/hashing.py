# [C5-REAL] Exergy-Maximized

import hashlib
from collections.abc import Mapping
from typing import Any

from cortex.utils.canonical import canonical_json


def canonical_json_bytes(payload: Any) -> bytes:
    """Return the exact UTF-8 bytes used for canonical JSON hashing."""
    return canonical_json(payload).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Return a SHA-256 hex digest for already-canonicalized bytes."""
    return hashlib.sha256(data).hexdigest()


def manifest_sha256(manifest: Mapping[str, Any]) -> str:
    """Compute the SHA-256 digest of a manifest excluding its own hash."""
    body = dict(manifest)
    body.pop("manifest_sha256", None)
    return sha256_hex(canonical_json_bytes(body))
