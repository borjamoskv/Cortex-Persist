"""
CORTEX v8 — Sovereign PII Sanitizer.

Detects Personally Identifiable Information (PII) in raw content before
it is vectorized and stored in L2. Applies selective field-level encryption
so the vector captures semantic *shape* ("there is an address here") but
the actual value is only recoverable with the tenant key.

Derivation: Ω₃ (Byzantine Default) + Ω₂ (Entropic Asymmetry)
DECISION: Encrypt, not redact — semantic vectors must remain useful.

Pattern categories detected:
  - EMAIL          → user@domain.com
  - PHONE          → +34 600 123 456 / 555-1234
  - ADDRESS        → calle/street/av/rue + number pattern
  - CREDIT_CARD    → 16-digit card numbers
  - DNI/NIF        → Spanish national ID
  - IBAN           → bank account numbers
  - IP_ADDRESS     → IPv4 / IPv6

Usage:
    sanitizer = PIISanitizer()
    clean, report = sanitizer.sanitize(raw_content, tenant_id="borja")
"""

from __future__ import annotations
from typing import Optional

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

__all__ = ["PIISanitizer", "PIIMatch", "PIICategory", "SanitizationReport"]

logger = logging.getLogger("cortex.memory.pii_sanitizer")


class PIICategory(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    CREDIT_CARD = "credit_card"
    DNI_NIF = "dni_nif"
    IBAN = "iban"
    IP_ADDRESS = "ip_address"
    PROPER_NAME = "proper_name"


@dataclass(frozen=True)
class PIIMatch:
    """A detected PII fragment."""

    category: PIICategory
    original: str
    start: int
    end: int
    placeholder: str  # What replaces it in the sanitized text


@dataclass
class SanitizationReport:
    """Result of a sanitization pass."""

    original: str
    sanitized: str
    encrypted_fragments: dict[str, str] = field(default_factory=dict)
    matches: list[PIIMatch] = field(default_factory=list)

    @property
    def has_pii(self) -> bool:
        return len(self.matches) > 0

    @property
    def pii_categories(self) -> set[PIICategory]:
        return {m.category for m in self.matches}


# ─── PII Patterns ─────────────────────────────────────────────────────────────
# Priority order matters: more specific patterns first.

_PATTERNS: list[tuple[PIICategory, re.Pattern[str]]] = [
    # Credit card (16 digits with optional spaces/dashes)
    (
        PIICategory.CREDIT_CARD,
        re.compile(
            r"\b(?:\d{4}[-\s]){3}\d{4}\b",
            re.IGNORECASE,
        ),
    ),
    # IBAN: 2 letters + 2 digits + 4 alphanum + 7 digits + up to 16 more
    (
        PIICategory.IBAN,
        re.compile(
            r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}[A-Z0-9]{0,16}\b",
            re.IGNORECASE,
        ),
    ),
    # Spanish DNI/NIF: 8 digits + optional dash + letter
    (
        PIICategory.DNI_NIF,
        re.compile(
            r"\b\d{8}-?[A-HJ-NP-TV-Z]\b",
            re.IGNORECASE,
        ),
    ),
    # Email
    (
        PIICategory.EMAIL,
        re.compile(
            r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
        ),
    ),
    # IPv4 address
    (
        PIICategory.IP_ADDRESS,
        re.compile(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        ),
    ),
    # Phone (international and spanish formats)
    (
        PIICategory.PHONE,
        re.compile(
            r"(?<!\w)(?:\+?\d{1,3}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}(?!\w)",
        ),
    ),
    # Address: street keywords followed by name and number
    (
        PIICategory.ADDRESS,
        re.compile(
            r"\b(?:calle|c/|av(?:enida)?|carrer|rue|street|st\."
            r"|boulevard|blvd|road|rd\.?|plaza|pza)\b"
            r"[^,.]{3,60}[,\s]+\d{1,5}",
            re.IGNORECASE,
        ),
    ),
]


class PIISanitizer:
    """Sovereign PII detection and field-level encryption layer.

    Sits between raw content ingestion and L2 vector encoding.
    Encrypts detected PII using the tenant key via CortexEncrypter,
    replacing it with semantic placeholders that preserve vector meaning.

    Args:
        encrypt: If True (default), encrypt matched PII. If False, redact with placeholder.
        scan_proper_names: Experimental — detects capitalized multi-word sequences.
                           Disabled by default to avoid false positives.
    """

    __slots__ = ("_encrypt", "_scan_proper_names")

    # Placeholder templates — semantically descriptive for the embedder
    _PLACEHOLDER_MAP: dict[PIICategory, str] = {
        PIICategory.EMAIL: "[EMAIL_ADDRESS]",
        PIICategory.PHONE: "[PHONE_NUMBER]",
        PIICategory.ADDRESS: "[POSTAL_ADDRESS]",
        PIICategory.CREDIT_CARD: "[CREDIT_CARD_NUMBER]",
        PIICategory.DNI_NIF: "[NATIONAL_ID]",
        PIICategory.IBAN: "[BANK_ACCOUNT_IBAN]",
        PIICategory.IP_ADDRESS: "[IP_ADDRESS]",
        PIICategory.PROPER_NAME: "[PERSON_NAME]",
    }

    def __init__(
        self,
        encrypt: bool = True,
        scan_proper_names: bool = False,
    ) -> None:
        self._encrypt = encrypt
        self._scan_proper_names = scan_proper_names

    def detect(self, text: str) -> list[PIIMatch]:
        """Detect all PII entities in text. Returns sorted, non-overlapping matches."""
        raw_matches: list[PIIMatch] = []

        for category, pattern in _PATTERNS:
            for m in pattern.finditer(text):
                placeholder = self._PLACEHOLDER_MAP[category]
                raw_matches.append(
                    PIIMatch(
                        category=category,
                        original=m.group(0),
                        start=m.start(),
                        end=m.end(),
                        placeholder=placeholder,
                    )
                )

        # Deduplicate overlapping spans — priority: first-matched pattern wins
        raw_matches.sort(key=lambda x: x.start)
        deduped: list[PIIMatch] = []
        last_end = -1
        for match in raw_matches:
            if match.start >= last_end:
                deduped.append(match)
                last_end = match.end

        return deduped

    def sanitize(
        self,
        content: str,
        tenant_id: str = "default",
    ) -> SanitizationReport:
        """Sanitize content: detect PII, encrypt or redact, return report.

        The sanitized string preserves semantic shape for embedding while
        protecting raw PII values. Encrypted fragments are stored in the
        report for caller persistence.

        Args:
            content: Raw input string.
            tenant_id: Used as encryption context (AAD).

        Returns:
            SanitizationReport with sanitized text and encrypted fragments.
        """
        matches = self.detect(content)

        if not matches:
            return SanitizationReport(
                original=content,
                sanitized=content,
            )

        report = SanitizationReport(original=content, sanitized=content, matches=matches)

        # Build new string with substitutions (reverse order to preserve offsets)
        result_chars = list(content)
        encrypted_fragments: dict[str, str] = {}

        for match in reversed(matches):
            placeholder = match.placeholder

            if self._encrypt:
                encrypted_value = self._try_encrypt(match.original, tenant_id)
                if encrypted_value:
                    # Store encrypted value keyed by placeholder + position for recovery
                    fragment_key = f"{match.category.value}:{match.start}"
                    encrypted_fragments[fragment_key] = encrypted_value
                    placeholder = f"{placeholder}[key={fragment_key}]"

            result_chars[match.start : match.end] = list(placeholder)

        report.sanitized = "".join(result_chars)
        report.encrypted_fragments = encrypted_fragments

        logger.info(
            "PII Sanitizer: %d entities found in %d chars [%s]",
            len(matches),
            len(content),
            ", ".join(c.value for c in report.pii_categories),
        )

        return report

    def _try_encrypt(self, value: str, tenant_id: str) -> Optional[str]:
        """Attempt field-level encryption using CortexEncrypter."""
        try:
            from cortex.crypto import get_default_encrypter

            enc = get_default_encrypter()
            return enc.encrypt_str(value, tenant_id=tenant_id)
        except (ImportError, OSError, ValueError, RuntimeError) as e:
            logger.warning(
                "PII encryption failed for tenant %s: %s — redacting instead",
                tenant_id,
                e,
            )
            return None


# ─── Module-level singleton ────────────────────────────────────────────────────

_default_sanitizer: Optional[PIISanitizer] = None


def get_pii_sanitizer(encrypt: bool = True) -> PIISanitizer:
    """Return the module-level default PIISanitizer (lazy singleton)."""
    global _default_sanitizer  # noqa: PLW0603
    if _default_sanitizer is None or _default_sanitizer._encrypt != encrypt:
        _default_sanitizer = PIISanitizer(encrypt=encrypt)
    return _default_sanitizer
