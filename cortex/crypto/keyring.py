"""
CORTEX v6 — Secure Keychain integration.
Never stores the CORTEX_MASTER_KEY in plain text .env unless forced (e.g., CI/CD).
"""

from __future__ import annotations

import base64
import logging
import os

try:
    import keyring
except ImportError:  # pragma: no cover - exercised via blocked-import tests
    keyring = None  # type: ignore[assignment]

_AES_KEY_LENGTH = 32  # 256 bits

logger = logging.getLogger(__name__)

SERVICE_NAME = "cortex_v6"
KEY_NAME = "master_key"
_keyring_error_types: tuple[type[Exception], ...]

if keyring is None:
    _keyring_error_types = (Exception,)
else:
    _errors = getattr(keyring, "errors", None)
    _keyring_cls = getattr(_errors, "KeyringError", Exception)
    _keyring_error_types = (_keyring_cls, OSError)


def get_master_key() -> bytes | None:
    """Read the master key from the OS keychain or fallback to env var."""
    key_b64 = None
    if keyring is not None and not os.environ.get("CORTEX_TESTING"):
        try:
            key_b64 = keyring.get_password(SERVICE_NAME, KEY_NAME)
        except _keyring_error_types as e:
            logger.warning("Failed to access OS Keychain: %s", e)

    if not key_b64:
        key_b64 = os.environ.get("CORTEX_MASTER_KEY")
        if not key_b64:
            key_b64 = os.environ.get("CORTEX_VAULT_KEY")

    if key_b64:
        try:
            raw = base64.b64decode(key_b64, validate=True)
            if len(raw) != _AES_KEY_LENGTH:
                logger.error(
                    "Master key has wrong length: got %d bytes, expected %d.",
                    len(raw),
                    _AES_KEY_LENGTH,
                )
                return None
            return raw
        except (ValueError, base64.binascii.Error):
            logger.error("Master key is not valid base64.")
            return None

    return None


def generate_and_store_master_key() -> str:
    """Generate a new AES-256 master key and store it in the OS Keychain."""
    key = os.urandom(_AES_KEY_LENGTH)
    key_b64 = base64.b64encode(key).decode("utf-8")

    if keyring is None:
        logger.warning(
            "OS Keychain integration unavailable. "
            "Set CORTEX_MASTER_KEY or CORTEX_VAULT_KEY manually with the generated key."
        )
        return key_b64

    try:
        keyring.set_password(SERVICE_NAME, KEY_NAME, key_b64)
        logger.info("Successfully vaulted new CORTEX_MASTER_KEY in OS Keychain.")
    except _keyring_error_types as e:
        logger.error(
            "Could not store key in Keychain (%s). "
            "Set CORTEX_MASTER_KEY env var manually with the generated key.",
            e,
        )

    return key_b64
