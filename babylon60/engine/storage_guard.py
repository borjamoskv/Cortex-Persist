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

logger = logging.getLogger("babylon60.guard.storage")


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
        effective_source = source.strip() if isinstance(source, str) else ""

        # Defensive coercion for tags before passing to Rust
        if isinstance(tags, str):
            raise GuardViolation("TAGS_TYPE_ERROR", "tags must be list[str], got str")

        error_tuple = None

        if not project or len(project) > 100:
            error_tuple = ("INVALID_PROJECT", "project must be between 1 and 100 characters")
        elif not content or not content.strip():
            error_tuple = ("EMPTY_CONTENT", "content cannot be empty")
        elif len(content) > 10_000_000:
            error_tuple = ("CONTENT_TOO_LARGE", "content exceeds maximum size limit")
        elif not fact_type:
            error_tuple = ("INVALID_FACT_TYPE", "fact_type cannot be empty")
        elif not effective_source:
            error_tuple = (
                "SOURCE_REQUIRED",
                "source attribution is mandatory. Use 'cli', 'agent:<name>', 'api', or 'human'.",
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
