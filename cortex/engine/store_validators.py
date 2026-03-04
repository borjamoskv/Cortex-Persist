"""store_validators — Content validation and deduplication for the Store Layer.

Extracted from StoreMixin to satisfy the Landauer LOC barrier (≤500).
These are pure functions: no side effects beyond raising ValueError on rejection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

__all__ = [
    "MIN_CONTENT_LENGTH",
    "validate_content",
    "check_dedup",
]

MIN_CONTENT_LENGTH = 10


def validate_content(project: str, content: str, fact_type: str) -> str:
    """Sovereign Content Gatekeeper — validates and normalizes content before storage."""
    if not project or not project.strip():
        raise ValueError("project cannot be empty")
    if not content or not content.strip():
        raise ValueError("content cannot be empty")

    content = content.strip()
    if len(content) < MIN_CONTENT_LENGTH:
        raise ValueError(f"content too short ({len(content)} chars, min {MIN_CONTENT_LENGTH})")

    if fact_type == "decision" and content.startswith("DECISION: DECISION:"):
        content = content.replace("DECISION: DECISION:", "DECISION:", 1)

    return content


async def check_dedup(
    conn: aiosqlite.Connection,
    tenant_id: str,
    project: str,
    content: str,
) -> int | None:
    """Verify if fact already exists with Zero-G entropy penalty.

    Uses content hash (not ciphertext) to safely bypass AES-GCM nonce variance.
    Returns the existing fact_id if a duplicate is found, else None.
    """
    from cortex.utils.canonical import compute_fact_hash

    f_hash = compute_fact_hash(content)

    cursor = await conn.execute(
        "SELECT id FROM facts WHERE tenant_id = ? AND project = ? AND hash = ? "
        "AND valid_until IS NULL AND is_quarantined = 0 LIMIT 1",
        (tenant_id, project, f_hash),
    )
    existing = await cursor.fetchone()
    if existing:
        return existing[0]
    return None
