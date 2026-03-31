"""
CORTEX Immutable Vote Ledger.

Almacenamiento de votos a prueba de manipulaciones criptográficas mediante
encadenamiento de hashes y árboles de Merkle.
Parte de la Arquitectura de Soberanía Wave 5.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("cortex.ledger")


class ImmutableVoteLedger:
    """
    Libro de votos inmutable. Cada entrada se enlaza al hash de la anterior.
    Implementa tenant isolation a nivel criptográfico.
    """

    def __init__(self, db_connection: Any):
        self.conn = db_connection

    async def get_last_hash(self, tenant_id: str) -> Optional[str]:
        """Obtiene el hash de la última entrada para un tenant específico."""
        cursor = await self.conn.execute(
            "SELECT hash FROM vote_ledger WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None

    def _compute_hash(
        self,
        tenant_id: str,
        prev_hash: Optional[str],
        fact_id: int,
        agent_id: str,
        vote: str,
        vote_weight: float,
        timestamp: str,
    ) -> str:
        """Calcula el hash SHA-256 de una entrada, incluyendo el tenant_id."""
        payload = {
            "tenant_id": tenant_id,
            "prev_hash": prev_hash,
            "fact_id": fact_id,
            "agent_id": agent_id,
            "vote": vote,
            "vote_weight": vote_weight,
            "timestamp": timestamp,
        }
        dump = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(dump.encode()).hexdigest()

    async def append_vote(
        self,
        fact_id: int,
        agent_id: str,
        vote: str,
        tenant_id: str,
        vote_weight: float = 1.0,
        signature: Optional[str] = None,
    ) -> str:
        """
        Añade un voto al ledger, calculando el nuevo hash encadenado.
        """
        async with self.conn.transaction():
            prev_hash = await self.get_last_hash(tenant_id)
            timestamp = datetime.now(timezone.utc).isoformat()

            entry_hash = self._compute_hash(
                tenant_id,
                prev_hash,
                fact_id,
                agent_id,
                vote,
                vote_weight,
                timestamp,
            )

            await self.conn.execute(
                """
                INSERT INTO vote_ledger
                (tenant_id, fact_id, agent_id, vote, vote_weight, prev_hash,
                 hash, timestamp, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    fact_id,
                    agent_id,
                    vote,
                    vote_weight,
                    prev_hash,
                    entry_hash,
                    timestamp,
                    signature,
                ),
            )
            await self.conn.commit()
            logger.info(
                "Vote appended to ledger: %s... (fact #%d)",
                entry_hash[:8],
                fact_id,
            )
            return entry_hash

    async def verify_chain(self, tenant_id: str) -> bool:
        """
        Verifica la integridad de la cadena para un tenant.
        Retorna True si todos los hashes coinciden.
        """
        cursor = await self.conn.execute(
            "SELECT * FROM vote_ledger WHERE tenant_id = ? ORDER BY id ASC",
            (tenant_id,),
        )
        rows = await cursor.fetchall()

        current_prev_hash = None
        for row in rows:
            # row indices based on schema:
            # 0:id, 1:tenant_id, 2:fact_id, 3:agent_id, 4:vote, 5:vote_weight,
            # 6:prev_hash, 7:hash, 8:timestamp, 9:signature
            calc_hash = self._compute_hash(
                tenant_id=row[1],
                prev_hash=row[6],
                fact_id=row[2],
                agent_id=row[3],
                vote=row[4],
                vote_weight=row[5],
                timestamp=row[8],
            )

            if calc_hash != row[7]:
                logger.error("Hash mismatch at entry ID %s", row[0])
                return False

            if row[6] != current_prev_hash:
                logger.error("Chain broken at entry ID %s", row[0])
                return False

            current_prev_hash = row[7]

        return True

    async def get_merkle_root(self, tenant_id: str) -> Optional[str]:
        """Obtiene la última raíz de Merkle capturada para el tenant."""
        cursor = await self.conn.execute(
            "SELECT root_hash FROM vote_merkle_roots WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None

    async def checkpoint_merkle_root(self, tenant_id: str) -> str:
        """
        Calcula y persiste una raíz de Merkle de todos los votos actuales del tenant.
        Esto permite verificaciones rápidas de 'estado global' del ledger.
        """
        cursor = await self.conn.execute(
            "SELECT hash FROM vote_ledger WHERE tenant_id = ? ORDER BY id ASC",
            (tenant_id,),
        )
        hashes = [row[0] for row in await cursor.fetchall()]

        if not hashes:
            return ""

        root = self._build_merkle_tree(hashes)
        timestamp = datetime.now(timezone.utc).isoformat()

        await self.conn.execute(
            "INSERT INTO vote_merkle_roots (tenant_id, root_hash, timestamp) VALUES (?, ?, ?)",
            (tenant_id, root, timestamp),
        )
        await self.conn.commit()
        return root

    def _build_merkle_tree(self, hashes: list[str]) -> str:
        """Algoritmo recursivo de Merkle Tree."""
        if not hashes:
            return ""
        if len(hashes) == 1:
            return hashes[0]

        new_level = []
        for i in range(0, len(hashes), 2):
            left = hashes[i]
            right = hashes[i + 1] if i + 1 < len(hashes) else left
            combined = hashlib.sha256((left + right).encode()).hexdigest()
            new_level.append(combined)

        return self._build_merkle_tree(new_level)
