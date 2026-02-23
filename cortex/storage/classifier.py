"""
CORTEX v6.7 — Privacy-Aware Data Classifier.

Detects sensitive information (API keys, secrets, PII, tokens) in facts
to prevent accidental synchronization to cloud backends.

Pattern coverage: 11 categories, 3 severity tiers.
"""

from __future__ import annotations

import logging
import re
from typing import Final

__all__ = ["DataSensitivity", "classify_content", "SECRET_PATTERNS"]

logger = logging.getLogger("cortex.storage.classifier")

# ── Pattern Registry ──────────────────────────────────────────────────
# Tier 1 (Critical, score=1.0): private keys, connection strings, SSH
# Tier 2 (High, score=0.8):     platform tokens (GitHub, GitLab, JWT)
# Tier 3 (Standard, score=0.7): generic API keys, cloud provider keys

SECRET_PATTERNS: Final[dict[str, str]] = {
    # Tier 1 — Critical
    "private_key": r"-----BEGIN (RSA|OPENSSH|EC|PGP|DSA) PRIVATE KEY-----",
    "connection_string": (
        r"(mongodb\+srv|postgres|postgresql|mysql|redis|mongodb|amqp)"
        r"://[a-zA-Z0-9_]+:[a-zA-Z0-9_!@#$%^&*]+@"
    ),
    "ssh_key": r"ssh-(rsa|ed25519|ecdsa|dss) AAAA[0-9A-Za-z+/]",
    # Tier 2 — Platform Tokens
    "github_token": r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}",
    "gitlab_token": r"glpat-[A-Za-z0-9\-_]{20,}",
    "jwt_token": r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_\-]{10,}",
    # Tier 3 — Cloud & Generic
    "generic_api_key": (
        r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token)"
        r"['\"\s]*[:=]['\"\s]*([a-zA-Z0-9_\-\.]{16,})"
    ),
    "stripe_key": r"sk_(live|test)_[a-zA-Z0-9]{24,}",
    "aws_key": r"AKIA[0-9A-Z]{16}",
    "google_api": r"AIza[0-9A-Za-z\-_]{35}",
    "slack_token": r"xox[bporas]-[A-Za-z0-9\-]{10,}",
}

CRITICAL_PATTERNS: Final[frozenset[str]] = frozenset(
    {
        "private_key",
        "connection_string",
        "ssh_key",
    }
)

PLATFORM_PATTERNS: Final[frozenset[str]] = frozenset(
    {
        "github_token",
        "gitlab_token",
        "jwt_token",
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
      - Tier 2 (Platform): score=0.8 — GitHub/GitLab/JWT tokens
      - Tier 3 (Standard): score=0.7 — generic API keys, cloud keys
    """
    matches: list[str] = []
    score = 0.0

    for name, pattern in SECRET_PATTERNS.items():
        if re.search(pattern, content):
            matches.append(name)
            if name in CRITICAL_PATTERNS:
                score = 1.0
            elif name in PLATFORM_PATTERNS:
                score = max(score, 0.8)
            else:
                score = max(score, 0.7)

    return DataSensitivity(score, matches)
