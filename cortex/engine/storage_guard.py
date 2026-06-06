# [C5-REAL] Exergy-Maximized
"""StorageGuard - Mandatory pre-store middleware.

No fact reaches the database without passing through this guard.
This is NOT opt-in. CortexEngine.store() calls it automatically.

Enforces:
1. Source attribution - every fact must have a source
2. Privacy classification - delegates to PrivacyMixin (blocks unclassified sensitive data)
3. Content integrity - size limits, poisoning detection (delegates to MCPGuard)
4. Fact type whitelist - only allowed types pass
5. Project validation - non-empty, reasonable length

Copyright 2026 by borjamoskv.com - Apache-2.0
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["GuardViolation", "StorageGuard"]

logger = logging.getLogger("cortex.guard.storage")


class GuardViolation(Exception):
    """Raised when a store operation violates a mandatory guard rule."""

    def __init__(self, rule: str, detail: str) -> None:
        self.rule = rule
        self.detail = detail
        super().__init__(f"[{rule}] {detail}")


class StorageGuard:
    """Mandatory pre-store validation middleware.

    Every store() call in CORTEX passes through StorageGuard.validate()
    BEFORE the fact touches the database. Guards are non-bypassable:
    they run inside _store_impl, not in an optional wrapper.
    """

    @classmethod
    def validate(
        cls,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        source: str | None = None,
        confidence: str = "stated",
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Run ALL mandatory pre-store checks via Rust Extension (PyO3).

        Raises GuardViolation with the specific rule that was violated.
        """
        effective_source = source or "unknown"
        
        # Defensive coercion for tags before passing to Rust
        if isinstance(tags, str):
            raise GuardViolation("TAGS_TYPE_ERROR", "tags must be list[str], got str")
        
        import cortex_rs
        
        error_tuple = cortex_rs.validate_proposal(
            project, content, fact_type, effective_source, confidence, tags
        )
        
        if error_tuple is not None:
            rule, detail = error_tuple
            raise GuardViolation(rule, detail)

        logger.debug(
            "StorageGuard PASS: project=%s, type=%s, source=%s, len=%d",
            project,
            fact_type,
            effective_source,
            len(content),
        )
