# [C5-REAL] Exergy-Maximized
"""
Apoptosis Daemon - Motor de Aniquilación Termodinámica.
Erradica físicamente nodos (facts) del Ledger cuyo horizonte epistémico 
(valid_until) haya expirado, liberando exergía en el sistema.
Ejecuta la LEY DE LANDAUER: Borrar memoria requiere validación BFT MTK.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from cortex.engine.mtk_core import MTKGuard
from cortex.storage.sqlite_adapter import SQLiteAdapter
from cortex.types.evidence import ClosurePayload, EvidenceBundle, Source

logger = logging.getLogger(__name__)

class ApoptosisDaemon:
    def __init__(self, mtk_guard: MTKGuard, db_adapter: SQLiteAdapter, check_interval_seconds: float = 3600.0):
        self.mtk_guard = mtk_guard
        self.db = db_adapter
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._apoptosis_loop())
        logger.info("[APOPTOSIS] Motor de purga activado.")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[APOPTOSIS] Motor de purga terminado.")

    async def _sweep_stale_nodes(self) -> int:
        """
        Detecta y aniquila (DELETE físico) los nodos caducados.
        Devuelve el conteo de nodos destruidos.
        """
        # Formato ISO para comparar con la base de datos (SQLite TIMESTAMPTZ store format)
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # Encontrar nodos expirados
        query = "SELECT id, content FROM facts WHERE valid_until IS NOT NULL AND valid_until < ?"
        stale_facts = await self.db.fetch_all(query, (now_iso,))
        
        if not stale_facts:
            return 0
            
        logger.warning(f"[APOPTOSIS] Detectados {len(stale_facts)} nodos obsoletos. Detonando aniquilación.")
        
        # 1. Empaquetar evidencia epistémica de por qué deben ser borrados
        claims = [
            {
                "action": "apoptosis",
                "reason": "temporal_decay",
                "target_node": str(fact["id"]),
                "content_preview": fact["content"][:50]
            }
            for fact in stale_facts
        ]
        
        evidence = EvidenceBundle.forge(
            query="stale_nodes_sweep",
            sources=[
                Source(
                    uri="cortex://daemon/apoptosis",
                    content_hash="system_clock_verification",
                    metadata={"time_horizon_breach": now_iso}
                )
            ],
            retrieved_at=datetime.now(timezone.utc)
        )
        
        # 2. Sellar el ClosurePayload
        payload = ClosurePayload.seal(
            claims=claims,
            evidence=evidence,
            verdict=True,
            proof_kind="stale_node_apoptosis"
        )
        
        # 3. Cruzar la barrera física del MTK
        try:
            async with self.mtk_guard.transaction_boundary(payload) as token:
                # 4. Aniquilación Causal en la DB (DELETE)
                ids_to_delete = tuple(fact["id"] for fact in stale_facts)
                placeholders = ",".join(["?"] * len(ids_to_delete))
                delete_query = f"DELETE FROM facts WHERE id IN ({placeholders})"
                
                await self.db.execute(delete_query, ids_to_delete)
                await self.db.commit()
                
                purged_count = len(ids_to_delete)
                logger.info(f"[APOPTOSIS] Poda Termodinámica exitosa. Nodos desintegrados: {purged_count}.")
                return purged_count
                
        except Exception as e:
            logger.error(f"[APOPTOSIS-FAIL] Falla al cruzar MTK para apoptosis: {e}")
            conn = await self.db.get_conn()
            await conn.rollback()
            return 0

    async def _apoptosis_loop(self) -> None:
        try:
            while self._running:
                await self._sweep_stale_nodes()
                await asyncio.sleep(self.check_interval_seconds)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("[APOPTOSIS] Error fatal en bucle de apoptosis: %s", e)
