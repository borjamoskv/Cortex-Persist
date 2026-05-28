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
import sqlite3
import time
from datetime import UTC, datetime
from typing import Any, Optional

logger = logging.getLogger("cortex.ledger")
GENESIS_PREV_HASH = "GENESIS"


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
        normalized_vote = int(vote)
        started_local_tx = not getattr(self.conn, "in_transaction", False)
        if started_local_tx:
            await self.conn.execute("BEGIN IMMEDIATE")
        try:
            prev_hash = await self.get_last_hash(tenant_id) or GENESIS_PREV_HASH
            timestamp = datetime.fromtimestamp(time.time(), tz=UTC).isoformat()

            entry_hash = self._compute_hash(
                tenant_id,
                prev_hash,
                fact_id,
                agent_id,
                normalized_vote,
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
                    normalized_vote,
                    vote_weight,
                    prev_hash,
                    entry_hash,
                    timestamp,
                    signature,
                ),
            )
            if started_local_tx:
                await self.conn.commit()
            logger.info(
                "Vote appended to ledger: %s... (fact #%d)",
                entry_hash[:8],
                fact_id,
            )
            return entry_hash
        except (sqlite3.Error, OSError, ValueError):
            if started_local_tx and getattr(self.conn, "in_transaction", False):
                await self.conn.rollback()
            raise

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

        current_prev_hash = GENESIS_PREV_HASH
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
            "SELECT id, hash FROM vote_ledger WHERE tenant_id = ? ORDER BY id ASC",
            (tenant_id,),
        )
        rows = await cursor.fetchall()
        hashes = [row[1] for row in rows]

        if not hashes:
            return ""

        root = self._build_merkle_tree(hashes)
        vote_start_id = int(rows[0][0])
        vote_end_id = int(rows[-1][0])
        vote_count = len(rows)

        await self.conn.execute(
            "INSERT INTO vote_merkle_roots "
            "(tenant_id, root_hash, vote_start_id, vote_end_id, vote_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (tenant_id, root, vote_start_id, vote_end_id, vote_count),
        )
        await self.conn.commit()
        return root

    async def create_checkpoint(self, tenant_id: str = "default") -> str:
        """Alias for checkpoint_merkle_root (CLI compatibility)."""
        return await self.checkpoint_merkle_root(tenant_id)

    async def verify_chain_integrity(self, tenant_id: str = "default") -> dict:
        """Verifica la cadena de hashes y retorna un informe detallado (CLI)."""
        try:
            cursor = await self.conn.execute(
                "SELECT * FROM vote_ledger WHERE tenant_id = ? ORDER BY id ASC",
                (tenant_id,),
            )
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                raise
            return {
                "valid": True,
                "votes_checked": 0,
                "checkpoints_checked": 0,
                "violations": [],
            }
        rows = await cursor.fetchall()

        violations = []
        current_prev_hash = GENESIS_PREV_HASH
        votes_checked = 0

        for row in rows:
            votes_checked += 1
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
                violations.append({"type": "hash_mismatch", "vote_id": row[0]})

            if row[6] != current_prev_hash:
                violations.append({"type": "chain_break", "vote_id": row[0]})

            current_prev_hash = row[7]

        return {
            "valid": len(violations) == 0,
            "votes_checked": votes_checked,
            "checkpoints_checked": await self._count_vote_checkpoints(tenant_id),
            "violations": violations,
        }

    async def _count_vote_checkpoints(self, tenant_id: str) -> int:
        try:
            cursor = await self.conn.execute(
                "SELECT COUNT(*) FROM vote_merkle_roots WHERE tenant_id = ?",
                (tenant_id,),
            )
            row = await cursor.fetchone()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                raise
            return 0
        return int(row[0]) if row else 0

    async def verify_merkle_roots(self, tenant_id: str = "default") -> list[dict]:
        """Verifica todas las raíces de Merkle registradas (CLI)."""
        try:
            cursor = await self.conn.execute(
                "SELECT id, root_hash, vote_start_id, vote_end_id, vote_count, created_at "
                "FROM vote_merkle_roots WHERE tenant_id = ? ORDER BY id ASC",
                (tenant_id,),
            )
            roots = await cursor.fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                raise
            return []

        report = []
        for r_id, root_hash, vote_start_id, vote_end_id, vote_count, created_at in roots:
            hash_cursor = await self.conn.execute(
                "SELECT hash FROM vote_ledger "
                "WHERE tenant_id = ? AND id >= ? AND id <= ? ORDER BY id ASC",
                (tenant_id, vote_start_id, vote_end_id),
            )
            vote_hashes = [row[0] for row in await hash_cursor.fetchall()]
            actual_root = self._build_merkle_tree(vote_hashes) if vote_hashes else ""
            valid = actual_root == root_hash and len(vote_hashes) == vote_count
            report.append(
                {
                    "checkpoint_id": r_id,
                    "valid": valid,
                    "expected": root_hash,
                    "actual": actual_root,
                    "created_at": created_at,
                    "vote_count": vote_count,
                }
            )
        return report

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
