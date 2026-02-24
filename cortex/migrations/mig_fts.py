import logging
import sqlite3

from cortex.crypto import get_default_encrypter

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

        # 2. Drop the existing virtual table (which is tied to facts)
        conn.execute("DROP TABLE IF EXISTS facts_fts")

        # 3. Create the new standalone FTS5 table
        conn.execute(
            "CREATE VIRTUAL TABLE facts_fts USING fts5(    content, project, tags, fact_type)"
        )
        logger.info("Migration 017: Recreated facts_fts as a standard FTS5 table")

        # 4. Repopulate facts_fts with decrypted content
        enc = get_default_encrypter()

        # Read all valid facts
        cursor = conn.execute(
            "SELECT id, content, project, tags, fact_type, tenant_id FROM facts WHERE valid_until IS NULL"
        )
        rows = cursor.fetchall()

        insert_count = 0
        for row in rows:
            fact_id, content_enc, project, tags_str, fact_type, tenant_id = row
            try:
                content_dec = enc.decrypt_str(content_enc, tenant_id=tenant_id)
                conn.execute(
                    "INSERT INTO facts_fts(rowid, content, project, tags, fact_type) VALUES (?, ?, ?, ?, ?)",
                    (fact_id, content_dec, project, tags_str, fact_type),
                )
                insert_count += 1
            except Exception as e:
                logger.warning(
                    f"Migration 017: Failed to decrypt or insert fact {fact_id} into FTS: {e}"
                )

        logger.info(
            f"Migration 017: Successfully repopulated facts_fts with {insert_count} decrypted facts"
        )

    except sqlite3.OperationalError as e:
        logger.warning(f"Migration 017: Operational error during FTS decoupling: {e}")
        raise
