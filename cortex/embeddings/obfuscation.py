# [C5-REAL] Exergy-Maximized
"""
Vector Obfuscation Engine (P-1 linear obfuscation).
Designed by Borja Moskv.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

import numpy as np


def get_obfuscation_key() -> bytes:
    """Load the master encryption/obfuscation key from environment."""
    key_str = (
        os.environ.get("CORTEX_VAULT_KEY")
        or os.environ.get("CORTEX_ENCRYPTION_KEY")
        or "default_cortex_static_obfuscation_key_seed"
    )
    try:
        return base64.b64decode(key_str)
    except Exception:
        return key_str.encode("utf-8")

def derive_pad_vector(dimension: int, tenant_id: str = "default", project: str = "") -> np.ndarray:
    """
    Derives a deterministic project-specific and tenant-specific pad vector (one-time pad).
    Uses HMAC-SHA256 based KDF to produce stable floats.
    """
    secret = get_obfuscation_key()
    context = f"{tenant_id}:{project}".encode()
    
    # Generate floats by expanding key
    okm = b""
    counter = 0
    while len(okm) < dimension * 4:
        h = hmac.new(secret, context + bytes([counter]), hashlib.sha256)
        okm += h.digest()
        counter += 1
        
    uints = np.frombuffer(okm[:dimension * 4], dtype=np.uint32)
    raw_floats = (uints.astype(np.float32) / 4294967295.0) * 2.0 - 1.0
    
    # Scale to specific small magnitude to maintain cosine similarity ranking stability.
    # Default scale factor is 0.1, configurable via CORTEX_OBFUSCATION_PAD_SCALE
    scale = float(os.environ.get("CORTEX_OBFUSCATION_PAD_SCALE", "0.1"))
    norm = np.linalg.norm(raw_floats)
    if norm > 0:
        raw_floats = (raw_floats / norm) * scale
        
    return raw_floats

def obfuscate_vector(
    vector: list[float],
    tenant_id: str = "default",
    project: str = "",
) -> list[float]:
    """
    Obfuscates an embedding vector by adding a derived static pad vector (one-time pad).
    If CORTEX_OBFUSCATE_EMBEDDINGS is not enabled or not set to '1'/'true', returns the vector unchanged.
    """
    enabled = os.environ.get("CORTEX_OBFUSCATE_EMBEDDINGS", "0").lower() in ("1", "true")
    if not enabled:
        return vector

    if not vector:
        return []
        
    arr = np.array(vector, dtype=np.float32)
    pad = derive_pad_vector(len(arr), tenant_id, project)
    
    # Linear addition: embedding + pad
    obfuscated = arr + pad
    return obfuscated.tolist()
