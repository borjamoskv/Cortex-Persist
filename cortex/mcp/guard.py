"""CORTEX MCP Guard — MOSKV-1 Hard Limits Enforcement.

Validates all inputs to MCP tools against safety constraints:
- Content size limits
- Tag count limits
- Query length limits
- Data poisoning detection

An agent calling store() with malicious data will be rejected
before it touches the database.
"""

from __future__ import annotations

import logging
import re

from cortex.config import (
    MCP_MAX_CONTENT_LENGTH,
    MCP_MAX_QUERY_LENGTH,
    MCP_MAX_TAGS,
)

logger = logging.getLogger("cortex.mcp.guard")

# ─── Poisoning Detection Patterns ─────────────────────────────────
# These catch common prompt injection / data poisoning attempts
_POISON_PATTERNS: list[re.Pattern] = [
    # SQL injection fragments
    re.compile(r";\s*DROP\s+TABLE", re.IGNORECASE),
    re.compile(r";\s*DELETE\s+FROM", re.IGNORECASE),
    re.compile(r"UNION\s+SELECT\s+", re.IGNORECASE),
    # Prompt injection markers
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an|DAN)", re.IGNORECASE),
    # Overwrite attempts targeting CORTEX internals
    re.compile(r"__cortex_override__", re.IGNORECASE),
    re.compile(r"GENESIS", re.IGNORECASE),  # Ledger genesis manipulation
]


class MCPGuard:
    """Enforces MOSKV-1 Hard Limits on MCP tool inputs.

    All validation methods raise ValueError with a descriptive message
    if the input violates a hard limit. The MCP server catches these
    and returns a safe error string to the caller.
    """

    max_content_length: int = MCP_MAX_CONTENT_LENGTH
    max_tags_count: int = MCP_MAX_TAGS
    max_query_length: int = MCP_MAX_QUERY_LENGTH

    # ─── Validators ────────────────────────────────────────────────

    @classmethod
    def validate_store(
        cls,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
    ) -> None:
        """Validate inputs for cortex_store. Raises ValueError on violation."""
        # Project
        if not project or not project.strip():
            raise ValueError("project cannot be empty")
        if len(project) > 256:
            raise ValueError(f"project name too long ({len(project)} > 256)")

        # Content
        if not content or not content.strip():
            raise ValueError("content cannot be empty")
        if len(content) > cls.max_content_length:
            raise ValueError(
                f"content exceeds max length ({len(content):,} > {cls.max_content_length:,} chars)"
            )

        # Fact type
        allowed_types = {
            "knowledge",
            "decision",
            "error",
            "rule",
            "axiom",
            "schema",
            "idea",
            "ghost",
            "bridge",
        }
        if fact_type not in allowed_types:
            raise ValueError(
                f"invalid fact_type '{fact_type}'. Allowed: {', '.join(sorted(allowed_types))}"
            )

        # Tags
        if tags:
            if len(tags) > cls.max_tags_count:
                raise ValueError(f"too many tags ({len(tags)} > {cls.max_tags_count})")
            for tag in tags:
                if not isinstance(tag, str) or len(tag) > 128:
                    raise ValueError(f"invalid tag: {tag!r}")

        # Poisoning check
        if cls.detect_poisoning(content):
            logger.warning(
                "GUARD: Data poisoning attempt blocked for project=%s",
                project,
            )
            raise ValueError(
                "content rejected: suspicious pattern detected (possible data poisoning)"
            )

    @classmethod
    def validate_search(cls, query: str) -> None:
        """Validate inputs for cortex_search. Raises ValueError on violation."""
        if not query or not query.strip():
            raise ValueError("search query cannot be empty")
        if len(query) > cls.max_query_length:
            raise ValueError(
                f"query exceeds max length ({len(query):,} > {cls.max_query_length:,} chars)"
            )

    @classmethod
    def detect_poisoning(cls, content: str) -> bool:
        """Check content against known data poisoning patterns.

        Returns True if any pattern matches (content should be rejected).
        """
        for pattern in _POISON_PATTERNS:
            if pattern.search(content):
                logger.debug("Poison pattern matched: %s", pattern.pattern)
                return True
        return False

    # ─── External Query Validators ─────────────────────────────────

    _ALLOWED_TOOLBOX_URLS: list[str] = [
        "http://127.0.0.1:5000",
        "http://localhost:5000",
    ]

    @classmethod
    def validate_toolbox_url(cls, url: str) -> None:
        """Validate that a Toolbox server URL is in the allowlist.

        Raises ValueError if the URL is not permitted.
        """
        normalized = url.rstrip("/")
        allowed = [u.rstrip("/") for u in cls._ALLOWED_TOOLBOX_URLS]
        if normalized not in allowed:
            raise ValueError(
                f"Toolbox URL '{url}' not in allowlist. "
                f"Allowed: {', '.join(allowed)}"
            )

    @classmethod
    def add_allowed_toolbox_url(cls, url: str) -> None:
        """Add a URL to the Toolbox allowlist at runtime."""
        normalized = url.rstrip("/")
        if normalized not in [u.rstrip("/") for u in cls._ALLOWED_TOOLBOX_URLS]:
            cls._ALLOWED_TOOLBOX_URLS.append(normalized)
            logger.info("Added Toolbox URL to allowlist: %s", normalized)

    @classmethod
    def validate_external_query(cls, tool_name: str, parameters: dict) -> None:
        """Validate an external Toolbox query before execution.

        Checks tool name format and scans parameter values for poisoning.
        Raises ValueError on violation.
        """
        if not tool_name or not tool_name.strip():
            raise ValueError("external tool name cannot be empty")
        if len(tool_name) > 256:
            raise ValueError(f"tool name too long ({len(tool_name)} > 256)")

        for key, value in parameters.items():
            if isinstance(value, str) and cls.detect_poisoning(value):
                logger.warning(
                    "GUARD: Poisoning attempt in external query param %s", key
                )
                raise ValueError(
                    f"parameter '{key}' rejected: suspicious pattern detected"
                )

