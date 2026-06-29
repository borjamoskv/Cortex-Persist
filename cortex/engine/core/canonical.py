# [C5-REAL] Exergy-Maximized
"""Canonical Serialization Engine (CEP-002).

Implements Deterministic CBOR and canonical map/set ordering
for CORTEX Epistemic Objects.
"""

import hashlib
from typing import Any

import cbor2


def _canonicalize(value: Any) -> Any:
    """Recursively enforce canonical byte ordering on collections."""
    if isinstance(value, dict):
        # Sort maps by key lexicographically by bytes
        # cbor2 actually has canonical options, but we explicitly order here to ensure
        # that keys are evaluated canonically. However, string keys are sorted naturally.
        return {k: _canonicalize(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    elif isinstance(value, (list, tuple)):
        return [_canonicalize(v) for v in value]
    elif isinstance(value, set):
        # Sets must be sorted by the byte value of their canonical elements
        # For simplicity in Python, we serialize each element, sort the serialized bytes,
        # and then we can store them as a list (since CBOR sets aren't standardly determinized).
        # We will represent sets as sorted lists.
        serialized_elements = [cbor2.dumps(_canonicalize(v), canonical=True) for v in value]
        sorted_elements = sorted(serialized_elements)
        return [cbor2.loads(b) for b in sorted_elements]
    return value

def canonical_serialize(obj: Any) -> bytes:
    """Serialize an object into Deterministic CBOR (RFC 8949)."""
    canonical_obj = _canonicalize(obj)
    return cbor2.dumps(canonical_obj, canonical=True)

def compute_object_hash(type_tag: str, obj: Any) -> str:
    """Compute the SHA3-256 hash of an EpistemicObject (CEP-002)."""
    cbor_bytes = canonical_serialize(obj)
    # Type prefixing with null byte separator
    prefix = f"{type_tag}\0".encode()
    h_input = prefix + cbor_bytes
    return hashlib.sha3_256(h_input).hexdigest()
