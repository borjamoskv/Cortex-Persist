# [C5-REAL] Exergy-Maximized
"""
Cryptographic Security.
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
    "CortexEncrypter",
    "Vault",
    "generate_and_store_master_key",
    "get_default_encrypter",
    "get_master_key",
    "RFC3161Client",
]

from .rfc3161 import RFC3161Client
