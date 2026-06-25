# [C5-REAL] Exergy-Maximized
"""
Motor de Epochs (The Antifragile-Robust Bridge).

Congela la matriz estocástica (alta frecuencia) en épocas criptográficas deterministas,
evitando el overhead de validar cada micro-voto en el hash chain.
"""

from __future__ import annotations

import logging
from typing import Any

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------

from cortex.consensus.vote_ledger import ImmutableVoteLedger

logger = logging.getLogger("cortex.epochs")


class EpochsEngine:
    """
    Motor que agrupa las transacciones asíncronas de la capa Antifrágil (Plano C)
    y las sella en el Ledger Inmutable (Plano A) mediante un Merkle Root.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def seal_epoch(self, tenant_id: str = "default") -> dict[str, Any]:
        """
        Sella un Epoch. Congela los votos actuales del tenant y genera un
        checkpoint criptográfico (Merkle Root) en el Ledger.
        
        En un modelo de producción, esto corre en segundo plano y sella 
        solo los votos acumulados desde el epoch anterior.
        """
        logger.info(f"Initiating Epoch seal for tenant: {tenant_id}")
        
        async with aiosqlite.connect(self.db_path) as conn:
            # WAL Mode and aggressive timeout (Rule R10 compliance for deadlocks)
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA busy_timeout=5000")
            
            ledger = ImmutableVoteLedger(conn)
            await ledger.ensure_tables()
            
            try:
                # Recuperar estado previo
                cursor = await conn.execute(
                    "SELECT id, status, merkle_root, last_vote_id FROM epoch_checkpoints WHERE tenant_id = ? ORDER BY id DESC LIMIT 1", 
                    (tenant_id,)
                )
                last_epoch = await cursor.fetchone()
                
                prev_root = None
                start_vote_id = 0
                
                if last_epoch:
                    epoch_id, status, prev_root, start_vote_id = last_epoch
                    if status == "computing":
                        # Recuperación de fallo: proceso murió en la Fase 2
                        logger.warning(f"Recovering failed Epoch {epoch_id} (computing -> sealed)")
                        # Usamos el start_vote_id de esa época fallida
                        # Re-calculamos de forma idempotente
                    else:
                        start_vote_id = start_vote_id or 0
                
                # Obtener el id máximo actual
                cursor = await conn.execute("SELECT MAX(id) FROM vote_ledger WHERE tenant_id = ?", (tenant_id,))
                max_id_row = await cursor.fetchone()
                end_vote_id = max_id_row[0] if max_id_row else 0
                
                if not end_vote_id or start_vote_id >= end_vote_id:
                    logger.info("No new votes to seal in this Epoch.")
                    return {"status": "skipped", "reason": "no_votes"}
                
                import time
                from datetime import datetime, timezone
                now_iso = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
                
                # FASE 1 (Prepare): Registrar intención de cálculo
                cursor = await conn.execute(
                    """INSERT INTO epoch_checkpoints 
                       (tenant_id, status, started_at, last_vote_id) 
                       VALUES (?, 'computing', ?, ?)""",
                    (tenant_id, now_iso, start_vote_id)
                )
                current_epoch_id = cursor.lastrowid
                await conn.commit()
                
                # FASE 2 (Commit): Calcular Merkle Root Incremental
                root_hash, vote_count, last_processed_id = await ledger.checkpoint_merkle_root(
                    tenant_id, 
                    start_vote_id=start_vote_id, 
                    end_vote_id=end_vote_id,
                    prev_root=prev_root
                )
                
                now_iso = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
                
                # Finalizar 2PC
                await conn.execute(
                    """UPDATE epoch_checkpoints 
                       SET status = 'sealed', sealed_at = ?, merkle_root = ?, vote_count = ?, last_vote_id = ?
                       WHERE id = ?""",
                    (now_iso, root_hash, vote_count, end_vote_id, current_epoch_id)
                )
                await conn.commit()
                
                logger.info(f"Epoch Sealed. Merkle Root: {root_hash[:16]}...")
                
                return {
                    "status": "sealed",
                    "tenant_id": tenant_id,
                    "merkle_root": root_hash,
                    "votes_processed": vote_count
                }
            except Exception as e:
                logger.error(f"Failed to seal epoch: {e}")
                # En un fallo fatal, el estado quedará en 'computing' y será retomado
                raise
