import asyncio
import sys
from pathlib import Path

import aiosqlite

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

import sqlite3

from cortex.engine import CortexEngine


async def main():
    db_path = str(Path("~/.cortex/cortex.db").expanduser())

    # Set SQLite Pragmas to avoid database is locked
    with sqlite3.connect(db_path) as init_db:
        init_db.execute("PRAGMA journal_mode=WAL")
        init_db.execute("PRAGMA synchronous=NORMAL")
        init_db.execute("PRAGMA busy_timeout=30000")

    engine = CortexEngine(db_path=db_path)

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, content, project, tenant_id FROM facts WHERE semantic_status IN ('pending', 'error') OR semantic_status IS NULL"
        )
        rows = await cursor.fetchall()

    print(f"Found {len(rows)} facts requiring enrichment.")
    for i, row in enumerate(rows):
        fact_id = row["id"]
        content = row["content"]
        if not content:
            print(f"[{i + 1}/{len(rows)}] Skipping fact {fact_id}: Empty content")
            continue

        project = row["project"] or "default"
        tenant_id = row["tenant_id"] or "default"

        max_retries = 5
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    print(f"[{i + 1}/{len(rows)}] Enriching fact {fact_id}...")
                await engine.embeddings.enrich_fact(fact_id, content, project, tenant_id)

                # Sanity check and Verification
                async with aiosqlite.connect(db_path, timeout=30.0) as upd_db:
                    cursor = await upd_db.execute(
                        "SELECT 1 FROM fact_embeddings WHERE fact_id = ?", (fact_id,)
                    )
                    if not await cursor.fetchone():
                        raise Exception("database is locked (silent embedding failure)")

                    await upd_db.execute(
                        "UPDATE facts SET semantic_status = 'completed' "
                        "WHERE id = ? AND semantic_status != 'completed'",
                        (fact_id,),
                    )
                    await upd_db.commit()
                break  # Success
            except Exception as e:
                err_str = str(e).lower()
                if "database is locked" in err_str or "locked" in err_str:
                    print(
                        f"[{i + 1}/{len(rows)}] DB locked on fact {fact_id}, "
                        f"retrying ({attempt + 1}/{max_retries})..."
                    )
                    await asyncio.sleep(2**attempt)
                else:
                    print(f"[{i + 1}/{len(rows)}] Failed to enrich fact {fact_id}: {e}")
                    break


if __name__ == "__main__":
    asyncio.run(main())
