import json
import logging
import sqlite3

from cortex.crypto import get_default_encrypter
from cortex.engine.fts_policy import should_index_plaintext_fts

logger = logging.getLogger("cortex")


def _migration_017_fts_decouple(conn: sqlite3.Connection):
    """
    Decouple facts_fts from the facts table to support encrypted facts
    while keeping FTS searchable with plaintext.
    Drops external content triggers and recreates facts_fts as a standalone
    FTS5 table, then repopulates it with decrypted content.
    """
    try:
        # 1. Drop the triggers that corrupt FTS when deleting/updating ciphertext
        conn.execute("DROP TRIGGER IF EXISTS facts_ai")
        conn.execute("DROP TRIGGER IF EXISTS facts_ad")
        conn.execute("DROP TRIGGER IF EXISTS facts_au")
        conn.execute("DROP TRIGGER IF EXISTS trg_facts_fts_insert")
        conn.execute("DROP TRIGGER IF EXISTS trg_facts_fts_update")
        conn.execute("DROP TRIGGER IF EXISTS trg_facts_fts_delete")
        conn.execute("DROP TRIGGER IF EXISTS trg_facts_ai")
        conn.execute("DROP TRIGGER IF EXISTS trg_facts_ad")
        conn.execute("DROP TRIGGER IF EXISTS trg_facts_au")

        # 2. Drop the existing virtual table (which is tied to facts)
        conn.execute("DROP TABLE IF EXISTS facts_fts")

        # 3. Create the new standalone FTS5 table
        conn.execute(
            "CREATE VIRTUAL TABLE facts_fts USING fts5("
            "content, project, tags, fact_type, tenant_id UNINDEXED)"
        )
        logger.info("Migration 017: Recreated facts_fts as a standard FTS5 table")

        # 4. Repopulate facts_fts with decrypted content
        enc = get_default_encrypter()

        # Read all valid facts
        cursor = conn.execute(
            "SELECT id, content, project, tags, fact_type, tenant_id, metadata "
            "FROM facts WHERE valid_until IS NULL"
        )
        rows = cursor.fetchall()

        insert_count = 0
        skipped_fact_ids: list[int] = []
        for row in rows:
            fact_id, content_enc, project, tags_str, fact_type, tenant_id, metadata_raw = row
            try:
                metadata = json.loads(metadata_raw) if metadata_raw else {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}
            if not should_index_plaintext_fts(metadata):
                continue
            try:
                content_dec = enc.decrypt_str(content_enc, tenant_id=tenant_id)
                conn.execute(
                    "INSERT INTO facts_fts(rowid, content, project, tags, fact_type, tenant_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (fact_id, content_dec, project, tags_str, fact_type, tenant_id),
                )
                insert_count += 1
            except (ValueError, TypeError, OSError) as e:
                skipped_fact_ids.append(int(fact_id))
                logger.error(
                    "Migration 017: Failed to decrypt or insert fact %s into FTS: %s", fact_id, e
                )

        if skipped_fact_ids:
            raise RuntimeError(
                "Migration 017 aborted: facts_fts rebuild skipped "
                f"{len(skipped_fact_ids)} fact(s): {skipped_fact_ids[:10]}"
            )

        logger.info(
            "Migration 017: Successfully repopulated facts_fts with %s decrypted facts",
            insert_count,
        )

    except sqlite3.OperationalError as e:
        logger.warning("Migration 017: Operational error during FTS decoupling: %s", e)
        raise
