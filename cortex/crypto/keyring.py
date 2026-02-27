"""
CORTEX v6 — Secure Keychain integration.
Never stores the CORTEX_MASTER_KEY in plain text .env unless forced (e.g., CI/CD).
"""

from __future__ import annotations

import base64
import logging
import os

import keyring

_AES_KEY_LENGTH = 32  # 256 bits

logger = logging.getLogger(__name__)

SERVICE_NAME = "cortex_v6"
KEY_NAME = "master_key"


def get_master_key() -> bytes | None:
    """Read the master key from the OS keychain or fallback to env var."""
    key_b64 = None
    if not os.environ.get("CORTEX_TESTING"):
        try:
            key_b64 = keyring.get_password(SERVICE_NAME, KEY_NAME)
        except (keyring.errors.KeyringError, OSError) as e:
            logger.warning("Failed to access OS Keychain: %s", e)

    if not key_b64:
        key_b64 = os.environ.get("CORTEX_MASTER_KEY")
        if not key_b64:
            key_b64 = os.environ.get("CORTEX_VAULT_KEY")

    if key_b64:
        try:
            raw = base64.b64decode(key_b64)
            if len(raw) != _AES_KEY_LENGTH:
                logger.error(
                    "Master key has wrong length: got %d bytes, expected %d.",
                    len(raw),
                    _AES_KEY_LENGTH,
                )
                return None
            return raw
        except (ValueError, Exception):
            logger.error("Master key is not valid base64.")
            return None

    return None


def generate_and_store_master_key() -> str:
    """Generate a new AES-256 master key and store it in the OS Keychain."""
    key = os.urandom(_AES_KEY_LENGTH)
    key_b64 = base64.b64encode(key).decode("utf-8")

    try:
        keyring.set_password(SERVICE_NAME, KEY_NAME, key_b64)
        logger.info("Successfully vaulted new CORTEX_MASTER_KEY in OS Keychain.")
    except (keyring.errors.KeyringError, OSError) as e:
        logger.error(
            "Could not store key in Keychain (%s). "
            "Set CORTEX_MASTER_KEY env var manually with the generated key.",
            e,
        )

    return key_b64
