"""store_validators — Content validation and deduplication for the Store Layer.

Extracted from StoreMixin to satisfy the Landauer LOC barrier (≤500).
These are pure functions: no side effects beyond raising ValueError on rejection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

__all__ = [
    "normalize_project",
    "validate_content",
    "check_dedup",
    "MIN_CONTENT_LENGTH",
]

MIN_CONTENT_LENGTH = 10


def normalize_project(raw: str) -> str:
    """Canonicalize project name to UPPER_SNAKE_CASE at write time.

    Enforces a single dedup namespace per logical project, preventing
    CORTEX/cortex-style splits that bypass the (tenant_id, project, hash)
    deduplication gate in check_dedup.
    """
    from cortex.utils.canonical import canonical_project_id

    return canonical_project_id(raw)


def validate_content(project: str, content: str, fact_type: str) -> str:
    """Sovereign Content Gatekeeper — normalizes content before storage.

    Note: Structural requirements (minimum length, poisoning checks, non-empty)
    are now enforced deterministically by StorageGuard via Pydantic upstream.
    This function handles business-logic specific normalizations only.
    """
    if fact_type == "decision" and content.startswith("DECISION: DECISION:"):
        content = content.replace("DECISION: DECISION:", "DECISION:", 1)

    return content


async def check_dedup(
    conn: aiosqlite.Connection,
    tenant_id: str,
    project: str,
    content: str,
    exclude_id: int | None = None,
) -> int | None:
    """Verify if fact already exists with Zero-G entropy penalty.

    Uses content hash (not ciphertext) to safely bypass AES-GCM nonce variance.
    Returns the existing fact_id if a duplicate is found, else None.
    """
    from cortex.utils.canonical import compute_fact_hash

    f_hash = compute_fact_hash(content)

    query = (
        "SELECT id FROM facts WHERE tenant_id = ? AND project = ? AND hash = ? "
        "AND is_tombstoned = 0 AND is_quarantined = 0 AND valid_until IS NULL"
    )
    params: list[str | int] = [tenant_id, project, f_hash]

    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)

    query += " LIMIT 1"

    async with conn.execute(query, tuple(params)) as cursor:
        existing = await cursor.fetchone()
    if existing:
        return existing[0]
    return None
