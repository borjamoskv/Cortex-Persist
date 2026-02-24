"""
CORTEX v6.7 — Privacy-Aware Data Classifier v2.

Detects sensitive information (API keys, secrets, PII, tokens) in facts
to prevent accidental synchronization to cloud backends.

Pattern coverage: 25 categories, 4 severity tiers.
"""

from __future__ import annotations

import logging
import re
from typing import Final

__all__ = ["DataSensitivity", "classify_content", "SECRET_PATTERNS"]

logger = logging.getLogger("cortex.storage.classifier")

# ── Pattern Registry ──────────────────────────────────────────────────
# Tier 1 (Critical, score=1.0): private keys, connection strings, SSH
# Tier 2 (PII, score=0.9):      personal identifiable information
# Tier 3 (High, score=0.8):     platform tokens (GitHub, GitLab, JWT, cloud)
# Tier 4 (Standard, score=0.7): generic API keys, cloud provider keys, infra tokens

SECRET_PATTERNS: Final[dict[str, str]] = {
    # ── Tier 1 — Critical (score=1.0) ───────────────────────────────
    "private_key": r"-----BEGIN (RSA|OPENSSH|EC|PGP|DSA) PRIVATE KEY-----",
    "connection_string": (
        r"(mongodb\+srv|postgres|postgresql|mysql|redis|mongodb|amqp)"
        r"://[a-zA-Z0-9_]+:[a-zA-Z0-9_!@#$%^&*]+@"
    ),
    "ssh_key": r"ssh-(rsa|ed25519|ecdsa|dss) AAAA[0-9A-Za-z+/]",

    # ── Tier 2 — PII (score=0.9) ────────────────────────────────────
    "email_address": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone_number": (
        r"(?<!\d)(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?"
        r"\d{3}[-.\s]?\d{4}(?!\d)"
    ),
    "ssn": r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)",
    "credit_card": r"(?<!\d)(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6011)[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}(?!\d)",
    "passport_number": r"(?i)passport[\s:#]*[A-Z0-9]{6,12}",

    # ── Tier 3 — Platform Tokens (score=0.8) ────────────────────────
    "github_token": r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}",
    "gitlab_token": r"glpat-[A-Za-z0-9\-_]{20,}",
    "jwt_token": r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_\-]{10,}",
    "azure_key": r"(?i)(AccountKey|azure[_-]?api[_-]?key)\s*[=:]\s*[A-Za-z0-9+/=]{20,}",
    "gcp_service_account": r'"type"\s*:\s*"service_account"',
    "heroku_api_key": r"(?i)heroku[_-]?api[_-]?key\s*[=:]\s*[a-f0-9\-]{36}",
    "twilio_key": r"(?:AC|SK)[a-f0-9]{32}",
    "sendgrid_key": r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}",

    # ── Tier 4 — Generic & Infra (score=0.7) ────────────────────────
    "generic_api_key": (
        r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token)"
        r"['\"\s]*[:=]['\"\s]*([a-zA-Z0-9_\-\.]{16,})"
    ),
    "stripe_key": r"sk_(live|test)_[a-zA-Z0-9]{24,}",
    "aws_key": r"AKIA[0-9A-Z]{16}",
    "google_api": r"AIza[0-9A-Za-z\-_]{35}",
    "slack_token": r"xox[bporas]-[A-Za-z0-9\-]{10,}",
    "npm_token": r"npm_[A-Za-z0-9]{36}",
    "pypi_token": r"pypi-[A-Za-z0-9_-]{50,}",
    "docker_auth": r'"auth"\s*:\s*"[A-Za-z0-9+/=]{20,}"',
}

CRITICAL_PATTERNS: Final[frozenset[str]] = frozenset(
    {
        "private_key",
        "connection_string",
        "ssh_key",
    }
)

PII_PATTERNS: Final[frozenset[str]] = frozenset(
    {
        "email_address",
        "phone_number",
        "ssn",
        "credit_card",
        "passport_number",
    }
)

PLATFORM_PATTERNS: Final[frozenset[str]] = frozenset(
    {
        "github_token",
        "gitlab_token",
        "jwt_token",
        "azure_key",
        "gcp_service_account",
        "heroku_api_key",
        "twilio_key",
        "sendgrid_key",
    }
)


class DataSensitivity:
    """Result of a data sensitivity analysis."""

    __slots__ = ("score", "matches")

    def __init__(self, score: float, matches: list[str]):
        self.score = score  # 0.0 (Public) → 1.0 (Critical)
        self.matches = matches

    @property
    def is_sensitive(self) -> bool:
        return self.score > 0.3

    def __repr__(self) -> str:
        return f"DataSensitivity(score={self.score}, matches={self.matches})"


def classify_content(content: str) -> DataSensitivity:
    """Analyze content for sensitive patterns.

    Returns a DataSensitivity with tiered scoring:
      - Tier 1 (Critical): score=1.0 — private keys, DB strings, SSH
      - Tier 2 (PII):      score=0.9 — email, phone, SSN, credit card
      - Tier 3 (Platform): score=0.8 — GitHub/GitLab/JWT/cloud tokens
      - Tier 4 (Standard): score=0.7 — generic API keys, infra tokens
    """
    matches: list[str] = []
    score = 0.0

    for name, pattern in SECRET_PATTERNS.items():
        if re.search(pattern, content):
            matches.append(name)
            if name in CRITICAL_PATTERNS:
                score = 1.0
            elif name in PII_PATTERNS:
                score = max(score, 0.9)
            elif name in PLATFORM_PATTERNS:
                score = max(score, 0.8)
            else:
                score = max(score, 0.7)

    return DataSensitivity(score, matches)
