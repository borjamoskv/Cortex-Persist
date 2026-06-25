# [C5-REAL] Exergy-Maximized
"""
Prueba Empírica del Apoptosis Daemon (LEY 10).
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import aiosqlite

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from cortex.engine.apoptosis_daemon import ApoptosisDaemon
from cortex.engine.mtk_core import MTKGuard
from cortex.storage.pg_schema import PG_CREATE_FACTS
from cortex.storage.sqlite_adapter import SQLiteAdapter


async def run_test():
    print("[TEST] Inicializando entorno para Apoptosis Daemon...")
    
    # 1. Base de datos en memoria
    conn = await aiosqlite.connect(":memory:")
    db = SQLiteAdapter(conn)
    
    create_table = """
    CREATE TABLE IF NOT EXISTS facts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id       TEXT NOT NULL DEFAULT 'default',
        project         TEXT NOT NULL,
        content         TEXT NOT NULL,
        fact_type       TEXT NOT NULL DEFAULT 'knowledge',
        tags            TEXT NOT NULL DEFAULT '[]',
        confidence      TEXT NOT NULL DEFAULT 'stated',
        valid_from      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        valid_until     TEXT,
        source          TEXT,
        meta            TEXT DEFAULT '{}',
        consensus_score REAL DEFAULT 0.5,
        hash            TEXT,
        signature       TEXT
    );
    """
    await db.executescript(create_table)
    
    # 2. Insertar nodos (facts)
    now = datetime.now(timezone.utc)
    stale_date = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    fresh_date = (now + timedelta(days=5)).isoformat().replace("+00:00", "Z")
    
    insert_sql = """
        INSERT INTO facts (tenant_id, project, content, fact_type, tags, confidence, valid_from, valid_until)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # Nodo caducado
    await db.execute_insert(insert_sql, ("default", "test_proj", "STALE_NODE", "knowledge", "[]", "C5", "2020-01-01T00:00:00Z", stale_date))
    
    # Nodo fresco
    await db.execute_insert(insert_sql, ("default", "test_proj", "FRESH_NODE", "knowledge", "[]", "C5", "2020-01-01T00:00:00Z", fresh_date))
    
    await db.commit()
    
    # Verificar inserción
    rows = await db.fetch_all("SELECT * FROM facts")
    assert len(rows) == 2, f"Se esperaban 2 nodos, hay {len(rows)}"
    
    # 3. Configurar MTK Guard (mock key de 32 bytes en base64 o raw, MTKGuard usa string o raw key)
    # Import ed25519 to generate key
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    import base64
    priv_key = ed25519.Ed25519PrivateKey.generate()
    # mt_guard will extract private bytes if passed correctly.
    mtk_guard = MTKGuard(private_key=priv_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    ))
    
    # 4. Iniciar Apoptosis Daemon
    daemon = ApoptosisDaemon(mtk_guard, db)
    print("[TEST] Ejecutando Barrido Apoptótico...")
    purged = await daemon._sweep_stale_nodes()
    
    print(f"[TEST] Nodos purgados: {purged}")
    assert purged == 1, f"Se esperaba 1 nodo purgado, se purgaron {purged}"
    
    # 5. Verificación física post-poda
    rows_post = await db.fetch_all("SELECT content FROM facts")
    assert len(rows_post) == 1, f"Debería quedar 1 nodo, quedan {len(rows_post)}"
    assert rows_post[0]["content"] == "FRESH_NODE", "El nodo restante debe ser el nodo fresco."
    
    print("[SUCCESS] Apoptosis Daemon superó la validación causal. El nodo stale fue aniquilado físicamente respetando la LEY 10 (Weaponized Forgetting).")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(run_test())
