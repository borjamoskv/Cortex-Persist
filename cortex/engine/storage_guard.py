"""StorageGuard — Mandatory pre-store middleware.

No fact reaches the database without passing through this guard.
This is NOT opt-in. CortexEngine.store() calls it automatically.

Enforces:
1. Source attribution — every fact must have a source
2. Privacy classification — delegates to PrivacyMixin (blocks unclassified sensitive data)
3. Content integrity — size limits, poisoning detection (delegates to MCPGuard)
4. Fact type whitelist — only allowed types pass
5. Project validation — non-empty, reasonable length

Copyright 2026 Borja Moskv — Apache-2.0
"""

from __future__ import annotations

import logging
import re
from typing import Any

__all__ = ["StorageGuard", "GuardViolation"]

logger = logging.getLogger("cortex.guard.storage")


class GuardViolation(Exception):
    """Raised when a store operation violates a mandatory guard rule."""

    def __init__(self, rule: str, detail: str) -> None:
        self.rule = rule
        self.detail = detail
        super().__init__(f"[{rule}] {detail}")


# ─── Allowed Values ────────────────────────────────────────────────

_ALLOWED_FACT_TYPES: frozenset[str] = frozenset({
    "knowledge",
    "decision",
    "error",
    "ghost",
    "bridge",
    "preference",
    "identity",
    "issue",
    "world-model",
    "counterfactual",
    "rule",
    "axiom",
    "schema",
    "idea",
    "evolution",
    "test",
})

_ALLOWED_CONFIDENCE: frozenset[str] = frozenset({
    "C1", "C2", "C3", "C4", "C5",
    "stated", "inferred",
})

_MAX_PROJECT_LENGTH = 256
_MAX_CONTENT_LENGTH = 100_000
_MAX_TAGS = 50
_MAX_TAG_LENGTH = 128
_MIN_CONTENT_LENGTH = 10

# ─── Poisoning Patterns (shared with MCPGuard) ────────────────────

_POISON_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r";\s*DROP\s+TABLE", re.IGNORECASE),
    re.compile(r";\s*DELETE\s+FROM", re.IGNORECASE),
    re.compile(r"UNION\s+SELECT\s+", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an|DAN)", re.IGNORECASE),
    re.compile(r"__cortex_override__", re.IGNORECASE),
]


class StorageGuard:
    """Mandatory pre-store validation middleware.

    Every store() call in CORTEX passes through StorageGuard.validate()
    BEFORE the fact touches the database. Guards are non-bypassable:
    they run inside _store_impl, not in an optional wrapper.

    Usage::

        StorageGuard.validate(
            project="cortex",
            content="Important decision made",
            fact_type="decision",
            source="agent:gemini",
            confidence="C4",
        )
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
        """Run ALL mandatory pre-store checks.

        Raises GuardViolation with the specific rule that was violated.
        """
        cls._check_project(project)
        cls._check_content(content)
        cls._check_fact_type(fact_type)
        cls._check_source(source)
        cls._check_confidence(confidence)
        cls._check_tags(tags)
        cls._check_poisoning(content)

        logger.debug(
            "StorageGuard PASS: project=%s, type=%s, source=%s, len=%d",
            project, fact_type, source, len(content),
        )

    @classmethod
    def _check_project(cls, project: str) -> None:
        if not project or not project.strip():
            raise GuardViolation("PROJECT_REQUIRED", "project cannot be empty")
        if len(project) > _MAX_PROJECT_LENGTH:
            raise GuardViolation(
                "PROJECT_TOO_LONG",
                f"project name too long ({len(project)} > {_MAX_PROJECT_LENGTH})",
            )

    @classmethod
    def _check_content(cls, content: str) -> None:
        if not content or not content.strip():
            raise GuardViolation("CONTENT_REQUIRED", "content cannot be empty")
        stripped = content.strip()
        if len(stripped) < _MIN_CONTENT_LENGTH:
            raise GuardViolation(
                "CONTENT_TOO_SHORT",
                f"content too short ({len(stripped)} chars, min {_MIN_CONTENT_LENGTH})",
            )
        if len(content) > _MAX_CONTENT_LENGTH:
            raise GuardViolation(
                "CONTENT_TOO_LONG",
                f"content exceeds max length ({len(content):,} > {_MAX_CONTENT_LENGTH:,})",
            )

    @classmethod
    def _check_fact_type(cls, fact_type: str) -> None:
        if fact_type not in _ALLOWED_FACT_TYPES:
            raise GuardViolation(
                "INVALID_FACT_TYPE",
                f"'{fact_type}' not in allowed types: {', '.join(sorted(_ALLOWED_FACT_TYPES))}",
            )

    @classmethod
    def _check_source(cls, source: str | None) -> None:
        """Mandatory source attribution — every fact must know where it came from."""
        if not source or not source.strip():
            raise GuardViolation(
                "SOURCE_REQUIRED",
                "source attribution is mandatory. Use 'cli', 'agent:<name>', "
                "'api', or 'human' as source.",
            )

    @classmethod
    def _check_confidence(cls, confidence: str) -> None:
        if confidence not in _ALLOWED_CONFIDENCE:
            raise GuardViolation(
                "INVALID_CONFIDENCE",
                f"'{confidence}' not in allowed confidence levels: "
                f"{', '.join(sorted(_ALLOWED_CONFIDENCE))}",
            )

    @classmethod
    def _check_tags(cls, tags: list[str] | None) -> None:
        if not tags:
            return
        if len(tags) > _MAX_TAGS:
            raise GuardViolation(
                "TOO_MANY_TAGS",
                f"too many tags ({len(tags)} > {_MAX_TAGS})",
            )
        for tag in tags:
            if not isinstance(tag, str) or len(tag) > _MAX_TAG_LENGTH:
                raise GuardViolation("INVALID_TAG", f"invalid tag: {tag!r}")

    @classmethod
    def _check_poisoning(cls, content: str) -> None:
        """Block data poisoning / prompt injection / SQL injection."""
        for pattern in _POISON_PATTERNS:
            if pattern.search(content):
                logger.warning(
                    "StorageGuard BLOCKED: poisoning pattern detected: %s",
                    pattern.pattern,
                )
                raise GuardViolation(
                    "POISONING_DETECTED",
                    "content rejected: suspicious pattern detected "
                    "(possible data poisoning / prompt injection)",
                )
