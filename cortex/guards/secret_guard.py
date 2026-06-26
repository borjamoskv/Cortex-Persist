# [C5-REAL] Exergy-Maximized
"""
CORTEX - Secret Guard (OWASP LLM06).

Prevents sensitive API keys, cloud credentials, and private keys from being persisted
in the Ledger, even if encrypted. This is a deterministic structural gate.
"""

import logging
import re

logger = logging.getLogger("cortex.guards.secret")


class PlaintextSecretError(Exception):
    """Raised when a plaintext secret is detected before persistence."""

    pass


class SecretGuard:
    """OWASP LLM06: Sensitive Information Disclosure Guard."""

    SECRET_PATTERNS = [
        re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key
        re.compile(r"sk-[a-zA-Z0-9]{48}"),  # OpenAI API Key
        re.compile(r"sk_(?:live|test)_[0-9a-zA-Z]{24,}"),  # Stripe API Key
        re.compile(r"ghp_[0-9a-zA-Z]{36}"),  # GitHub PAT
        re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,}"),  # Slack Token
        re.compile(r"-----BEGIN (?:[A-Z0-9]+\s+)?PRIVATE KEY-----"),  # Private Keys (RSA, OpenSSH, PKCS#8 etc.)
        re.compile(r"AIzaSy[A-Za-z0-9_-]{33}"),  # Gemini API Key
        re.compile(r"sk-ant-[a-zA-Z0-9_-]{40,}"),  # Anthropic API Key
    ]

    @classmethod
    def verify_clean(cls, content: str) -> None:
        """
        Scans content for known secrets.
        Raises PlaintextSecretError (P0 Abort) if found.
        """
        for pattern in cls.SECRET_PATTERNS:
            if pattern.search(content):
                logger.error("[P0] SecretGuard: Plaintext secret detected in memory proposal.")
                raise PlaintextSecretError(
                    "OWASP LLM06 Violation: Plaintext secret detected in persistence payload. Aborting SAGA."
                )
