"""
CORTEX v6 — Cryptographic Security.
"""

from .aes import CortexEncrypter, get_default_encrypter
from .vault import Vault


def get_master_key():
    """Lazily resolve the master-key loader to avoid hard import coupling."""
    from .keyring import get_master_key as _get_master_key

    return _get_master_key()


def generate_and_store_master_key():
    """Lazily resolve key generation so `cortex.crypto` imports stay portable."""
    from .keyring import generate_and_store_master_key as _generate_and_store_master_key

    return _generate_and_store_master_key()


__all__ = [
    "Vault",
    "get_master_key",
    "generate_and_store_master_key",
    "CortexEncrypter",
    "get_default_encrypter",
]
