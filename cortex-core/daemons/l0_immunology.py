import asyncio
import json
import sqlite3
import time
import logging
import uuid
import weakref

from persistence.base import DB_PATH, _get_local_conn, _setup_sqlite_pragmas
from daemons.outbox import enqueue_swarm_task

logger = logging.getLogger("L0_Immunology")

class ImmunologyDaemon:
    """L0 Immunology Daemon (SAGA Mutación 2.0).
    Asynchronously monitors the CORTEX Execution Ledger for entropy deaths (Falsations)
    and autonomously injects AST_MUTATION or EXA_LISP healing patches into the swarm queue.
    """

    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._daemon_task = None
        self._last_checked_id = 0
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=10.0)
        _setup_sqlite_pragmas(self._conn)
        self._finalizer = weakref.finalize(self, self._safe_close, self._conn)
        
        # Initialize highest ID to prevent retroactive patching
        self._sync_high_watermark()

    def _safe_close(self, conn):
        try:
            conn.close()
        except Exception:
            import logging
            logging.getLogger(__name__).error('DETECTIVE-OMEGA: Silent exception swallowed in l0_immunology.py')

    def close(self):
        if hasattr(self, "_finalizer") and self._finalizer.alive:
            self._finalizer.detach()
            self._safe_close(self._conn)

    def _sync_high_watermark(self):
        try:
            c = self._conn.cursor()
            c.execute("SELECT MAX(id) FROM cortex_execution_ledger")
            row = c.fetchone()
            if row and row[0]:
                self._last_checked_id = row[0]
        except sqlite3.OperationalError:
            import logging
            logging.getLogger(__name__).error('DETECTIVE-OMEGA: Silent exception swallowed in l0_immunology.py')

    def _synthesize_healing_payload(self, falsation_type: str, vector_id: str, context: str) -> dict:
        """
        Sovereign LLM Integration Hook.
        In a full deployment, this calls API-Provider-OMEGA to fetch a Qwen/Gemini response.
        For C5-REAL deterministic execution, we synthesize a bounded recovery patch.
        """
        patch_id = f"AUTOPOIESIS_{uuid.uuid4().hex[:8]}"
        
        logger.warning(f"Synthesizing healing patch {patch_id} for {vector_id} ({falsation_type})")
        
        # Default fallback: Re-evaluate with higher bounds or reset state
        payload = {
            "type": "AST_MUTATION",
            "target_vector": vector_id,
            "mutation_hash": patch_id,
            "action": "HEAL_ENTROPY",
            "reason": falsation_type,
            "timestamp": time.monotonic()
        }
        
        if falsation_type == "C5_FALSATED_ENTROPY":
            # Exergy death: Increase limits or simplify AST
            payload["exergy_boost"] = 5000.0
        elif falsation_type == "C5_FALSATED_SYNTAX":
            # Syntax death: Inject structural purge
            payload["ast_purge"] = True
            
        return payload

    async def _immunology_loop(self):
        logger.info("C5-REAL L0 Immunology Daemon Online. Monitoring for systemic entropy...")
        while True:
            await asyncio.sleep(2.0)  # Out-of-band monitoring interval
            try:
                c = self._conn.cursor()
                c.execute(
                    """
                    SELECT id, action, vector_id, yield_amount, timestamp 
                    FROM cortex_execution_ledger 
                    WHERE id > ? AND action LIKE 'C5_FALSATED_%'
                    ORDER BY id ASC LIMIT 50
                    """,
                    (self._last_checked_id,)
                )
                
                rows = c.fetchall()
                for row in rows:
                    row_id, action, vector_id, yield_amount, ts = row
                    self._last_checked_id = max(self._last_checked_id, row_id)
                    
                    logger.error(f"L0 Interceptor Detected Entropy: {action} on {vector_id} (Yield: {yield_amount})")
                    
                    # Synthesize LLM/Deterministic patch
                    healing_payload = self._synthesize_healing_payload(action, vector_id, str(yield_amount))
                    
                    # Inject back into O(1) Swarm RingBuffer
                    try:
                        target_agent = f"HEALER_{vector_id[:16]}"
                        enqueue_swarm_task(target_agent, healing_payload)
                        logger.info(f"Healing patch injected into ZeroCopyRingBuffer for {vector_id}")
                    except Exception as e:
                        logger.critical(f"Failed to inject healing patch: {e}")

            except sqlite3.OperationalError as e:
                logger.debug(f"Immunology ledger read error: {e}")
            except Exception as e:
                logger.error(f"Unexpected Immunology Daemon error: {e}")

    def start_guardian(self):
        if self._daemon_task:
            return
        try:
            loop = asyncio.get_running_loop()
            self._daemon_task = loop.create_task(self._immunology_loop())
        except RuntimeError:
            logger.warning("ImmunologyDaemon could not start: no active event loop.")
