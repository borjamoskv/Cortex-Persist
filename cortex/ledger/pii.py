from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cortex.ledger.models import LedgerEvent


class LedgerPIIError(ValueError):
    """Raised when a ledger event contains direct identifiers."""


DEFAULT_ALLOWED_METADATA_KEYS = frozenset(
    {
        "decision_ref",
        "parent_decision_id",
        "payload_ref",
        "project",
        "reason_code",
        "risk_ref",
        "subject_ref",
        "taint",
        "tenant_id",
        "trace_ref",
    }
)

FORBIDDEN_KEY_TOKENS = frozenset(
    {
        "account",
        "address",
        "customer_email",
        "email",
        "full_name",
        "iban",
        "name",
        "passport",
        "phone",
        "plaintext",
        "ssn",
        "user_email",
    }
)

OPAQUE_VALUE_KEYS = frozenset(
    {
        "hash",
        "origin_signature",
        "prev_hash",
        "public_key",
        "signature",
    }
)

DIRECT_IDENTIFIER_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\+\d{8,15}\b"),
    re.compile(r"\b\d{3}[\s.-]\d{3}[\s.-]\d{4}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
)


@dataclass(frozen=True)
class LedgerPIIPolicy:
    allowed_metadata_keys: frozenset[str] = DEFAULT_ALLOWED_METADATA_KEYS

    def validate_event(self, event: LedgerEvent) -> None:
        validate_no_direct_identifiers(
            event.to_payload(), allowed_metadata_keys=self.allowed_metadata_keys
        )


def validate_no_direct_identifiers(
    value: Any,
    *,
    allowed_metadata_keys: frozenset[str] = DEFAULT_ALLOWED_METADATA_KEYS,
    path: str = "event",
) -> None:
    if isinstance(value, str):
        if _contains_direct_identifier(value):
            raise LedgerPIIError(f"ledger_direct_identifier:{path}")
        return
    if isinstance(value, Mapping):
        _validate_mapping(value, allowed_metadata_keys=allowed_metadata_keys, path=path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_no_direct_identifiers(
                item,
                allowed_metadata_keys=allowed_metadata_keys,
                path=f"{path}[{index}]",
            )


def scrub_text(value: str) -> str:
    scrubbed = value
    for pattern in DIRECT_IDENTIFIER_PATTERNS:
        scrubbed = pattern.sub("[REDACTED]", scrubbed)
    return scrubbed


def _validate_mapping(
    value: Mapping[Any, Any],
    *,
    allowed_metadata_keys: frozenset[str],
    path: str,
) -> None:
    for key, item in value.items():
        key_text = str(key)
        child_path = f"{path}.{_safe_path_token(key_text)}"
        _validate_key(key_text, child_path)
        if path == "event.metadata" and key_text not in allowed_metadata_keys:
            raise LedgerPIIError(f"ledger_metadata_key_not_allowlisted:{child_path}")
        if key_text in OPAQUE_VALUE_KEYS:
            continue
        validate_no_direct_identifiers(
            item,
            allowed_metadata_keys=allowed_metadata_keys,
            path=child_path,
        )


def _validate_key(key: str, path: str) -> None:
    normalized = key.lower().replace("-", "_")
    if _contains_direct_identifier(key):
        raise LedgerPIIError(f"ledger_direct_identifier_key:{path}")
    if normalized in FORBIDDEN_KEY_TOKENS:
        raise LedgerPIIError(f"ledger_forbidden_identifier_key:{path}")


def _contains_direct_identifier(value: str) -> bool:
    return any(pattern.search(value) for pattern in DIRECT_IDENTIFIER_PATTERNS)


def _safe_path_token(value: str) -> str:
    if not value or _contains_direct_identifier(value):
        return "<redacted-key>"
    return re.sub(r"[^A-Za-z0-9_:-]", "_", value)[:64]
