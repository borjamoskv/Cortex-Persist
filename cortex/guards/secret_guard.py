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
        re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),  # AWS Access / Session Keys
        re.compile(r"\bsk-(?:proj-|live-)?[a-zA-Z0-9_-]{32,}\b"),  # OpenAI API Key
        re.compile(r"sk_(?:live|test)_[0-9a-zA-Z]{24,}"),  # Stripe API Key
        re.compile(
            r"(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9_]{36}|github_pat_[a-zA-Z0-9_]{82}"
        ),  # GitHub PAT / OAuth Tokens
        re.compile(r"glpat-[a-zA-Z0-9_-]{20,}"),  # GitLab PAT
        re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,}"),  # Slack Token
        re.compile(
            r"-----BEGIN (?:[A-Z0-9\s_-]+)?PRIVATE KEY-----"
        ),  # Private Keys (OpenSSH, EC, RSA, ENCRYPTED, PGP, etc.)
        re.compile(r"AIzaSy[A-Za-z0-9_-]{33}"),  # Gemini API Key
        re.compile(r"sk-ant-[a-zA-Z0-9_-]{40,}"),  # Anthropic API Key
        re.compile(
            r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]+"
        ),  # JWT Tokens (Azure, Auth0, etc.)
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
