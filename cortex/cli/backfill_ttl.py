"""
CORTEX — TTL Backfill Script.

Applies expires_at to existing facts that were stored before
TTL governance was implemented. Respects permanent fact types.

Usage:
    cd ~/cortex && .venv/bin/python -m cortex.cli.backfill_ttl
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

logger = logging.getLogger("cortex.backfill_ttl")

__all__ = ["backfill_ttl"]

# TTL defaults (days) per fact_type. None = permanent.
_TTL_DEFAULTS: dict[str, int | None] = {
    "ghost": 30,
    "error": 90,
    "decision": 180,
    "knowledge": 180,
    "bridge": 180,
    "identity": None,
    "axiom": None,
    "rule": None,
    "schema": None,
    "preference": None,
}
_TTL_FALLBACK_DAYS = 90


def _compute_expires_at(fact_type: str, created_at: str) -> str | None:
    """Compute expires_at from fact_type TTL and creation timestamp.

    Returns ISO timestamp or None if the type is permanent.
    """
    ttl_days = _TTL_DEFAULTS.get(fact_type, _TTL_FALLBACK_DAYS)
    if ttl_days is None:
        return None
    created = datetime.fromisoformat(created_at)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (created + timedelta(days=ttl_days)).isoformat()


async def backfill_ttl(db_path: str | None = None) -> dict[str, int]:
    """Apply TTL to existing facts based on their fact_type and created_at.

    Returns:
        Dict with counts: scanned, updated, permanent, errors.
    """
    path = db_path or str(Path("~/.cortex/cortex.db").expanduser())
    stats = {"scanned": 0, "updated": 0, "permanent": 0, "errors": 0}

    async with aiosqlite.connect(path) as conn:
        cursor = await conn.execute(
            "SELECT id, fact_type, created_at FROM facts "
            "WHERE expires_at IS NULL AND valid_until IS NULL "
            "ORDER BY id ASC"
        )
        rows = await cursor.fetchall()
        stats["scanned"] = len(rows)

        for fact_id, fact_type, created_at in rows:
            expires_at = _compute_expires_at(fact_type, created_at)

            if expires_at is None:
                stats["permanent"] += 1
                continue

            try:
                await conn.execute(
                    "UPDATE facts SET expires_at = ? WHERE id = ?",
                    (expires_at, fact_id),
                )
                stats["updated"] += 1

                if stats["updated"] % 200 == 0:
                    await conn.commit()
                    logger.info("Backfilled TTL for %d facts...", stats["updated"])

            except (ValueError, OSError, TypeError) as e:
                logger.warning("Failed to backfill TTL for fact %d: %s", fact_id, e)
                stats["errors"] += 1

        await conn.commit()

    logger.info(
        "📅 TTL backfill: scanned=%d, updated=%d, permanent=%d, errors=%d",
        stats["scanned"], stats["updated"],
        stats["permanent"], stats["errors"],
    )
    return stats


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = asyncio.run(backfill_ttl())
    print(  # noqa: T201
        f"\n✅ TTL Backfill: {result['updated']}/{result['scanned']} "
        f"facts given TTL, {result['permanent']} permanent"
    )
    if result["errors"] > 0:
        print(f"⚠️  Errors: {result['errors']}")  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    main()
