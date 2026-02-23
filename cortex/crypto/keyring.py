"""
CORTEX v6 — Secure Keychain integration.
Never stores the CORTEX_MASTER_KEY in plain text .env unless forced (e.g., CI/CD).
"""

import base64
import logging
import os

import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

SERVICE_NAME = "cortex_v6"
KEY_NAME = "master_key"


def get_master_key() -> bytes | None:
    """Read the master key from the OS keychain or fallback to env var."""
    key_b64 = None
    if not os.environ.get("CORTEX_TESTING"):
        try:
            key_b64 = keyring.get_password(SERVICE_NAME, KEY_NAME)
        except Exception as e:
            logger.warning(f"Failed to access OS Keychain: {e}")

    if not key_b64:
        key_b64 = os.environ.get("CORTEX_MASTER_KEY")
        if not key_b64:
            # Fallback to the old vault key if present during migration
            key_b64 = os.environ.get("CORTEX_VAULT_KEY")

    if key_b64:
        try:
            return base64.b64decode(key_b64)
        except ValueError:
            logger.error("Master key is not valid base64.")
            return None

    return None


def generate_and_store_master_key() -> str:
    """Generate a new AES-256 master key and store it in the OS Keychain."""
    key = AESGCM.generate_key(bit_length=256)
    key_b64 = base64.b64encode(key).decode("utf-8")

    try:
        keyring.set_password(SERVICE_NAME, KEY_NAME, key_b64)
        logger.info("Successfully vaulted new CORTEX_MASTER_KEY in OS Keychain.")
    except Exception as e:
        logger.error(
            f"Could not store key in Keychain ({e}). Set CORTEX_MASTER_KEY={key_b64} in .env manually."
        )

    return key_b64
