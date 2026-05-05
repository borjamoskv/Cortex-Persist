"""
CORTEX Immutable Vote Ledger.

Almacenamiento de votos a prueba de manipulaciones criptográficas mediante
encadenamiento de hashes, enlace explícito al hash del hecho y árboles Merkle.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from cortex.utils.canonical import canonical_json

logger = logging.getLogger("cortex.ledger")

_GENESIS_HASH = "GENESIS"
_DYNAMIC_TABLES = frozenset({"vote_ledger", "vote_merkle_roots"})


class ImmutableVoteLedger:
    """
    Libro de votos inmutable. Cada entrada se enlaza al hash anterior y al
    hash del hecho votado, manteniendo aislamiento criptográfico por tenant.
    """

    def __init__(self, db_connection: Any):
        self.conn = db_connection

    @staticmethod
    def _assert_dynamic_table(table_name: str) -> None:
        if table_name not in _DYNAMIC_TABLES:
            raise ValueError(f"Unsupported table name: {table_name}")

    async def _table_columns(self, table_name: str) -> set[str]:
        self._assert_dynamic_table(table_name)
        cursor = await self.conn.execute(f"PRAGMA table_info({table_name})")
        rows = await cursor.fetchall()
        return {str(row[1]) for row in rows}

    async def _ensure_schema(self) -> None:
        """Create or upgrade the vote ledger schema in-place."""
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vote_ledger (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id       TEXT NOT NULL DEFAULT 'default',
                fact_id         INTEGER NOT NULL REFERENCES facts(id),
                fact_hash       TEXT NOT NULL DEFAULT '',
                agent_id        TEXT NOT NULL,
                vote            INTEGER NOT NULL,
                vote_weight     REAL NOT NULL,
                prev_hash       TEXT NOT NULL,
                hash            TEXT NOT NULL,
                timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
                signature       TEXT,
                UNIQUE(hash)
            )
        """)
        columns = await self._table_columns("vote_ledger")
        if "fact_hash" not in columns:
            await self.conn.execute(
                "ALTER TABLE vote_ledger ADD COLUMN fact_hash TEXT NOT NULL DEFAULT ''"
            )

        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vote_ledger_fact ON vote_ledger(fact_id)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vote_ledger_fact_hash ON vote_ledger(fact_hash)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vote_ledger_agent ON vote_ledger(agent_id)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vote_ledger_timestamp ON vote_ledger(timestamp)"
        )
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vote_merkle_roots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id       TEXT NOT NULL DEFAULT 'default',
                root_hash       TEXT NOT NULL,
                vote_start_id   INTEGER NOT NULL,
                vote_end_id     INTEGER NOT NULL,
                vote_count      INTEGER NOT NULL,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(root_hash)
            )
        """)

    async def get_last_hash(self, tenant_id: str) -> Optional[str]:
        """Obtiene el hash de la última entrada para un tenant específico."""
        await self._ensure_schema()
        cursor = await self.conn.execute(
            "SELECT hash FROM vote_ledger WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None

    async def _lookup_fact_hash(self, fact_id: int, tenant_id: str) -> str:
        cursor = await self.conn.execute(
            "SELECT hash FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise ValueError(f"Fact {fact_id} not found for tenant {tenant_id}")
        fact_hash = row[0]
        if not fact_hash:
            raise ValueError(f"Fact {fact_id} has no hash; refusing unbound vote ledger entry")
        return str(fact_hash)

    async def _current_fact_hash(self, fact_id: int, tenant_id: str) -> Optional[str]:
        cursor = await self.conn.execute(
            "SELECT hash FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        row = await cursor.fetchone()
        return str(row[0]) if row and row[0] else None

    def _compute_hash(
        self,
        *,
        tenant_id: str,
        prev_hash: str,
        fact_id: int,
        fact_hash: str,
        agent_id: str,
        vote: str | int,
        vote_weight: float,
        timestamp: str,
        signature: Optional[str],
    ) -> str:
        """Calcula el hash SHA-256 canónico de una entrada."""
        payload = {
            "schema": "vote_ledger_v2",
            "tenant_id": tenant_id,
            "prev_hash": prev_hash,
            "fact_id": fact_id,
            "fact_hash": fact_hash,
            "agent_id": agent_id,
            "vote": str(vote),
            "vote_weight": vote_weight,
            "timestamp": timestamp,
            "signature": signature or "",
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()

    async def append_vote(
        self,
        fact_id: int,
        agent_id: str,
        vote: str | int,
        tenant_id: str,
        vote_weight: float = 1.0,
        signature: Optional[str] = None,
        *,
        commit: bool = True,
    ) -> str:
        """
        Añade un voto al ledger, enlazándolo al hash vigente del hecho.
        """
        await self._ensure_schema()
        prev_hash = await self.get_last_hash(tenant_id) or _GENESIS_HASH
        fact_hash = await self._lookup_fact_hash(fact_id, tenant_id)
        timestamp = datetime.now(timezone.utc).isoformat()
        entry_hash = self._compute_hash(
            tenant_id=tenant_id,
            prev_hash=prev_hash,
            fact_id=fact_id,
            fact_hash=fact_hash,
            agent_id=agent_id,
            vote=vote,
            vote_weight=vote_weight,
            timestamp=timestamp,
            signature=signature,
        )

        await self.conn.execute(
            """
            INSERT INTO vote_ledger
            (tenant_id, fact_id, fact_hash, agent_id, vote, vote_weight, prev_hash,
             hash, timestamp, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                fact_id,
                fact_hash,
                agent_id,
                str(vote),
                vote_weight,
                prev_hash,
                entry_hash,
                timestamp,
                signature,
            ),
        )
        if commit:
            await self.conn.commit()
        logger.info("Vote appended to ledger: %s... (fact #%d)", entry_hash[:8], fact_id)
        return entry_hash

    async def verify_chain(self, tenant_id: str) -> bool:
        """
        Verifica la integridad de la cadena para un tenant.
        Retorna True si todos los hashes coinciden.
        """
        report = await self.verify_chain_integrity(tenant_id=tenant_id)
        return bool(report["valid"])

    async def get_merkle_root(self, tenant_id: str) -> Optional[str]:
        """Obtiene la última raíz de Merkle capturada para el tenant."""
        await self._ensure_schema()
        cursor = await self.conn.execute(
            "SELECT root_hash FROM vote_merkle_roots WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None

    async def checkpoint_merkle_root(self, tenant_id: str) -> str:
        """
        Calcula y persiste una raíz Merkle de todos los votos actuales del tenant.
        """
        await self._ensure_schema()
        cursor = await self.conn.execute(
            "SELECT id, hash FROM vote_ledger WHERE tenant_id = ? ORDER BY id ASC",
            (tenant_id,),
        )
        rows = await cursor.fetchall()
        if not rows:
            return ""

        hashes = [str(row[1]) for row in rows]
        root = self._build_merkle_tree(hashes)
        timestamp = datetime.now(timezone.utc).isoformat()
        columns = await self._table_columns("vote_merkle_roots")
        values_by_column = {
            "tenant_id": tenant_id,
            "root_hash": root,
            "vote_start_id": int(rows[0][0]),
            "vote_end_id": int(rows[-1][0]),
            "vote_count": len(rows),
            "created_at": timestamp,
            "timestamp": timestamp,
        }
        insert_columns = [col for col in values_by_column if col in columns]
        placeholders = ", ".join("?" for _ in insert_columns)
        await self.conn.execute(
            f"INSERT OR IGNORE INTO vote_merkle_roots "
            f"({', '.join(insert_columns)}) VALUES ({placeholders})",
            [values_by_column[col] for col in insert_columns],
        )
        await self.conn.commit()
        return root

    async def create_checkpoint(self, tenant_id: str = "default") -> str:
        """Alias for checkpoint_merkle_root (CLI compatibility)."""
        return await self.checkpoint_merkle_root(tenant_id)

    async def verify_chain_integrity(self, tenant_id: str = "default") -> dict[str, Any]:
        """Verifica cadena, hashes de entrada y enlace al hash del hecho."""
        await self._ensure_schema()
        cursor = await self.conn.execute(
            """
            SELECT id, tenant_id, fact_id, agent_id, vote, vote_weight, prev_hash,
                   hash, timestamp, signature, fact_hash
            FROM vote_ledger
            WHERE tenant_id = ?
            ORDER BY id ASC
            """,
            (tenant_id,),
        )
        rows = await cursor.fetchall()

        violations: list[dict[str, Any]] = []
        current_prev_hash = _GENESIS_HASH
        votes_checked = 0

        for row in rows:
            votes_checked += 1
            (
                vote_id,
                row_tenant_id,
                fact_id,
                agent_id,
                vote,
                vote_weight,
                prev_hash,
                stored_hash,
                timestamp,
                signature,
                fact_hash,
            ) = row

            calc_hash = self._compute_hash(
                tenant_id=row_tenant_id,
                prev_hash=prev_hash,
                fact_id=fact_id,
                fact_hash=fact_hash,
                agent_id=agent_id,
                vote=vote,
                vote_weight=vote_weight,
                timestamp=timestamp,
                signature=signature,
            )
            if calc_hash != stored_hash:
                violations.append({"type": "hash_mismatch", "vote_id": vote_id})

            if prev_hash != current_prev_hash:
                violations.append(
                    {
                        "type": "chain_break",
                        "vote_id": vote_id,
                        "expected_prev_hash": current_prev_hash,
                        "actual_prev_hash": prev_hash,
                    }
                )

            if not fact_hash:
                violations.append({"type": "unbound_fact_hash", "vote_id": vote_id})
            else:
                current_fact_hash = await self._current_fact_hash(fact_id, row_tenant_id)
                if current_fact_hash is None:
                    violations.append({"type": "missing_fact", "vote_id": vote_id})
                elif current_fact_hash != fact_hash:
                    violations.append(
                        {
                            "type": "fact_hash_mismatch",
                            "vote_id": vote_id,
                            "fact_id": fact_id,
                            "expected_fact_hash": fact_hash,
                            "actual_fact_hash": current_fact_hash,
                        }
                    )

            current_prev_hash = stored_hash

        checkpoint_reports = await self.verify_merkle_roots(tenant_id=tenant_id)
        for checkpoint in checkpoint_reports:
            if not checkpoint["valid"]:
                violations.append(
                    {
                        "type": "vote_merkle_mismatch",
                        "checkpoint_id": checkpoint["checkpoint_id"],
                        "expected": checkpoint["expected"],
                        "actual": checkpoint["actual"],
                    }
                )

        return {
            "valid": len(violations) == 0,
            "votes_checked": votes_checked,
            "checkpoints_checked": len(checkpoint_reports),
            "violations": violations,
        }

    async def verify_merkle_roots(self, tenant_id: str = "default") -> list[dict[str, Any]]:
        """Verifica todas las raíces Merkle registradas."""
        await self._ensure_schema()
        columns = await self._table_columns("vote_merkle_roots")
        if {"vote_start_id", "vote_end_id", "vote_count"}.issubset(columns):
            cursor = await self.conn.execute(
                """
                SELECT id, root_hash, vote_start_id, vote_end_id, vote_count
                FROM vote_merkle_roots
                WHERE tenant_id = ?
                ORDER BY id ASC
                """,
                (tenant_id,),
            )
            roots = await cursor.fetchall()
            report = []
            for checkpoint_id, root_hash, start_id, end_id, expected_count in roots:
                vote_cursor = await self.conn.execute(
                    """
                    SELECT hash FROM vote_ledger
                    WHERE tenant_id = ? AND id BETWEEN ? AND ?
                    ORDER BY id ASC
                    """,
                    (tenant_id, start_id, end_id),
                )
                vote_hashes = [str(row[0]) for row in await vote_cursor.fetchall()]
                actual = self._build_merkle_tree(vote_hashes)
                valid = actual == root_hash and len(vote_hashes) == expected_count
                report.append(
                    {
                        "checkpoint_id": checkpoint_id,
                        "valid": valid,
                        "expected": root_hash,
                        "actual": actual,
                        "vote_start_id": start_id,
                        "vote_end_id": end_id,
                        "vote_count": len(vote_hashes),
                    }
                )
            return report

        cursor = await self.conn.execute(
            "SELECT id, root_hash FROM vote_merkle_roots WHERE tenant_id = ? ORDER BY id ASC",
            (tenant_id,),
        )
        roots = await cursor.fetchall()
        vote_cursor = await self.conn.execute(
            "SELECT hash FROM vote_ledger WHERE tenant_id = ? ORDER BY id ASC",
            (tenant_id,),
        )
        current_root = self._build_merkle_tree([str(row[0]) for row in await vote_cursor.fetchall()])
        return [
            {
                "checkpoint_id": checkpoint_id,
                "valid": root_hash == current_root,
                "expected": root_hash,
                "actual": current_root,
            }
            for checkpoint_id, root_hash in roots
        ]

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
            combined = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
            new_level.append(combined)

        return self._build_merkle_tree(new_level)
