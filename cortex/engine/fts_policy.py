"""FTS indexing policy for fact plaintext.

Facts are encrypted at rest, while FTS can only search plaintext. This module
keeps the plaintext index opt-out deterministic for sensitive facts.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

ALLOW_PLAINTEXT_FTS_ENV = "CORTEX_ALLOW_PLAINTEXT_FTS"
PRIVACY_FTS_THRESHOLD = Decimal("0.7")


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def should_index_plaintext_fts(meta: Mapping[str, Any] | None) -> bool:
    """Return False when fact metadata marks plaintext FTS as unsafe."""
    if _truthy(os.getenv(ALLOW_PLAINTEXT_FTS_ENV)):
        return True

    if not meta:
        return True

    if _truthy(meta.get("privacy_flagged")):
        return False

    privacy_score = _decimal_or_none(meta.get("privacy_score"))
    if privacy_score is not None and privacy_score >= PRIVACY_FTS_THRESHOLD:
        return False

    return True
