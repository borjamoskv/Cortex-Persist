import asyncio
import sqlite3
import numpy as np
import os
import json
import uuid
import logging

from cortex.utils import void_vec
from cortex.utils.void_mih import slice_void_bit
from cortex.memory.encoder import AsyncEncoder
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2
from cortex.memory.l2_hybrid_search import L2HybridSearch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OuroborosGenesis")

DB_PATH = os.path.expanduser("~/.cortex/vectors.db")

def drop_corrupt_indexes(conn):
    logger.info("🔪 [OUROBOROS] Dropping corrupt FTS5 and SQLite-Vec tables.")
    cur = conn.cursor()
    
    cur.execute("DROP TABLE IF EXISTS facts_meta_fts")
    cur.execute("DROP TRIGGER IF EXISTS facts_meta_fts_insert")
    cur.execute("DROP TRIGGER IF EXISTS facts_meta_fts_delete")
    cur.execute("DROP TRIGGER IF EXISTS facts_meta_fts_update")
    
    try:
        cur.execute("DROP TABLE IF EXISTS vec_facts")
        cur.execute("DROP TABLE IF EXISTS vec_void")
        cur.execute("DROP TABLE IF EXISTS vec_void_mih")
        
        # Also drop potential shards
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vec_facts_%'")
        for row in cur.fetchall():
            cur.execute(f"DROP TABLE IF EXISTS {row['name']}")
            
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vec_void_%'")
        for row in cur.fetchall():
            cur.execute(f"DROP TABLE IF EXISTS {row['name']}")
        logger.info("✅ Vector schema dropped.")
    except Exception as e:
        logger.warning(f"⚠️ Vector schema drop failed: {e}")

async def rebuild_indexes():
    # We use the official stack to regenerate embeddings
    logger.info("🔥 [OUROBOROS] Loading Sovereign Vector Engine.")
    encoder = AsyncEncoder()
    store = SovereignVectorStoreL2(encoder=encoder, db_path=DB_PATH)
    
    # Force connection and ensure schema
    conn = store._get_conn()
    
    # Drop tables NOW that sqlite_vec is loaded
    drop_corrupt_indexes(conn)
    
    # Force recreate the tables
    conn.executescript(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_facts USING vec0(
            embedding int8[{encoder.dimension}]
        );
        CREATE TABLE IF NOT EXISTS vec_void (
            rowid INTEGER PRIMARY KEY,
            embedding BLOB
        );
        CREATE TABLE IF NOT EXISTS vec_void_mih (
            rowid INTEGER PRIMARY KEY,
            s0 INTEGER, s1 INTEGER, s2 INTEGER, s3 INTEGER,
            s4 INTEGER, s5 INTEGER, s6 INTEGER, s7 INTEGER,
            s8 INTEGER, s9 INTEGER, s10 INTEGER, s11 INTEGER,
            s12 INTEGER, s13 INTEGER, s14 INTEGER, s15 INTEGER
        );
        """
    )
    for i in range(16):
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_void_mih_s{i} ON vec_void_mih(s{i})")

    hybrid = store.hybrid_search
    if hybrid is None:
        hybrid = L2HybridSearch(store)
        hybrid.ensure_fts_table()
        logger.info("✅ FTS5 Engine forcefully recreated.")

    # Now get all facts from meta and re-embed them
    cur = conn.cursor()
    cur.execute("SELECT rowid, id, tenant_id, project_id, content, storage_tier FROM facts_meta")
    rows = cur.fetchall()
    
    logger.info(f"🌌 [OUROBOROS] Re-quantizing and re-embedding {len(rows)} records into INT8.")
    
    # Process sequentially to avoid memory overload
    rebuild_count = 0
    for row in rows:
        rowid = row["rowid"]
        content = row["content"]
        tenant_id = row["tenant_id"]
        project_id = row["project_id"]
        tier = row["storage_tier"]
        
        if not content:
            continue
            
        emb_list = await encoder.encode(content)
        arr = np.array(emb_list, dtype=np.float32)
        int8_bytes = arr.tobytes()
        binary_bytes = void_vec.pack_void_bit(arr)
        
        # Get correct domain tables
        meta_tb, vec_tb, vec_void_tb, mih_tb = store._get_domain_tables(conn, tenant_id, project_id)
        
        insert_cur = conn.cursor()
        
        if vec_void_tb:
            insert_cur.execute(f"INSERT OR REPLACE INTO {vec_void_tb}(rowid, embedding) VALUES (?, ?)", (rowid, binary_bytes))
            # MIH shards
            shards = slice_void_bit(binary_bytes)
            insert_cur.execute(
                f"INSERT OR REPLACE INTO {mih_tb} (rowid, s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13, s14, s15) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rowid, *shards)
            )
            
        if tier != "COLD" and vec_tb:
            # We must use vec_quantize_int8 directly inside SQLite
            insert_cur.execute(
                f"INSERT OR REPLACE INTO {vec_tb}(rowid, embedding) "
                f"VALUES (?, vec_quantize_int8(?, 'unit'))",
                (rowid, int8_bytes)
            )
            
        rebuild_count += 1
        if rebuild_count % 50 == 0:
            logger.info(f"Processed {rebuild_count}/{len(rows)} records...")
            
    conn.commit()
    logger.info(f"✅ Ouroboros genesis complete. Re-quantized {rebuild_count} rows.")

async def main():
    await rebuild_indexes()
    
if __name__ == "__main__":
    asyncio.run(main())
