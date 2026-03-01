"""
CORTEX v7 — Rehash CLI Command.

Retroactively computes and fills SHA-256 hashes for facts
that were stored before hash integrity was implemented.

Usage:
    cd ~/cortex && .venv/bin/python -m cortex.cli.rehash_facts
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import sys
from pathlib import Path

import aiosqlite

from cortex.crypto import get_default_encrypter
from cortex.memory.temporal import now_iso
from cortex.utils.canonical import compute_fact_hash

logger = logging.getLogger("cortex.rehash")

__all__ = ["rehash_facts"]


async def rehash_facts(db_path: str | None = None) -> dict[str, int]:
    """Rehash all facts that have NULL hash and are still active.

    Returns:
        Dict with counts: total_scanned, rehashed, skipped, errors.
    """
    path = db_path or str(Path("~/.cortex/cortex.db").expanduser())
    enc = get_default_encrypter()
    stats = {"total_scanned": 0, "rehashed": 0, "skipped": 0, "errors": 0, "duplicates": 0}

    async with aiosqlite.connect(path) as conn:
        cursor = await conn.execute(
            "SELECT id, content, tenant_id FROM facts "
            "WHERE hash IS NULL AND valid_until IS NULL "
            "ORDER BY id ASC"
        )
        rows = await cursor.fetchall()
        stats["total_scanned"] = len(rows)

        for fact_id, encrypted_content, tenant_id in rows:
            try:
                # Decrypt content
                plaintext = enc.decrypt_str(encrypted_content, tenant_id=tenant_id)
                if not plaintext:
                    stats["skipped"] += 1
                    continue

                # Compute hash
                f_hash = compute_fact_hash(plaintext)

                # Update
                await conn.execute(
                    "UPDATE facts SET hash = ? WHERE id = ?",
                    (f_hash, fact_id),
                )
                stats["rehashed"] += 1

                if stats["rehashed"] % 100 == 0:
                    logger.info("Rehashed %d facts...", stats["rehashed"])
                    await conn.commit()

            except (aiosqlite.IntegrityError, sqlite3.IntegrityError):
                # Duplicate content in same project/tenant — deprecate the older dupe
                logger.debug("Duplicate hash for fact %d, deprecating", fact_id)
                await conn.execute(
                    "UPDATE facts SET valid_until = ?, hash = ? WHERE id = ?",
                    (now_iso(), f_hash, fact_id),
                )
                stats["duplicates"] += 1
            except (ValueError, OSError, TypeError) as e:
                logger.warning("Failed to rehash fact %d: %s", fact_id, e)
                stats["errors"] += 1

        await conn.commit()

    logger.info(
        "🔐 Rehash complete: scanned=%d, rehashed=%d, duplicates=%d, skipped=%d, errors=%d",
        stats["total_scanned"], stats["rehashed"],
        stats["duplicates"], stats["skipped"], stats["errors"],
    )
    return stats


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = asyncio.run(rehash_facts())
    print(f"\n✅ Rehash: {result['rehashed']}/{result['total_scanned']} facts updated")  # noqa: T201
    if result["duplicates"] > 0:
        print(f"🔀 Duplicates deprecated: {result['duplicates']}")  # noqa: T201
    if result["errors"] > 0:
        print(f"⚠️  Errors: {result['errors']}")  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    main()
