"""Sync operations mixin for CortexEngine.

Advanced synchronous operations: consensus voting, ledger,
deprecation, recall, temporal reconstruction, stats, and ghosts.
"""

from __future__ import annotations

import logging
import sqlite3

from cortex.engine.models import Fact
from cortex.engine.sync_ghost_mixin import SyncGhostMixin
from cortex.memory.temporal import now_iso

__all__ = ["SyncOpsMixin"]

logger = logging.getLogger("cortex")


class SyncOpsMixin(SyncGhostMixin):
    """Advanced synchronous operations for CortexEngine.

    Requires ``_get_sync_conn()`` from ``SyncCompatMixin``.
    """

    # ─── Consensus ──────────────────────────────────────────────

    def vote_sync(self, fact_id: int, agent: str, value: int) -> float:
        """Cast a v1 consensus vote synchronously.

        Args:
            fact_id: The fact to vote on.
            agent: Agent name.
            value: Vote value (-1, 0, or 1).

        Returns:
            Updated consensus score.
        """
        if value not in (-1, 0, 1):
            raise ValueError(f"vote value must be -1, 0, or 1, got {value}")
        conn = self._get_sync_conn()
        if value == 0:
            conn.execute(
                "DELETE FROM consensus_votes WHERE fact_id = ? AND agent = ?",
                (fact_id, agent),
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO consensus_votes (fact_id, agent, vote) VALUES (?, ?, ?)",
                (fact_id, agent, value),
            )
        # Recalculate consensus score
        row = conn.execute(
            "SELECT SUM(vote) FROM consensus_votes WHERE fact_id = ?",
            (fact_id,),
        ).fetchone()
        vote_sum = row[0] or 0
        score = max(0.0, 1.0 + (vote_sum * 0.1))
        if score >= 1.5:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = 'verified' WHERE id = ?",
                (score, fact_id),
            )
        elif score <= 0.5:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = 'disputed' WHERE id = ?",
                (score, fact_id),
            )
        else:
            conn.execute(
                "UPDATE facts SET consensus_score = ? WHERE id = ?",
                (score, fact_id),
            )
        conn.commit()
        return score

    # ─── Ledger (Sync) ──────────────────────────────────────────

    def _log_transaction_sync(self, conn, project, action, detail) -> int:
        """Synchronous version of _log_transaction."""
        from cortex.utils.canonical import canonical_json, compute_tx_hash

        dj = canonical_json(detail)
        ts = now_iso()
        cursor = conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
        prev = cursor.fetchone()
        ph = prev[0] if prev else "GENESIS"
        th = compute_tx_hash(ph, project, action, dj, ts)

        c = conn.execute(
            "INSERT INTO transactions "
            "(project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project, action, dj, ph, th, ts),
        )
        tx_id = c.lastrowid

        # Note: Auto-checkpoint is skipped in sync mode for now to avoid complexity
        return tx_id

    def deprecate_sync(self, fact_id: int, reason: str | None = None) -> bool:
        """Synchronous version of deprecate."""
        if not isinstance(fact_id, int) or fact_id <= 0:
            raise ValueError("Invalid fact_id")

        conn = self._get_sync_conn()
        ts = now_iso()
        cursor = conn.execute(
            "UPDATE facts SET valid_until = ?, updated_at = ?, "
            "meta = json_set(COALESCE(meta, '{}'), '$.deprecation_reason', ?) "
            "WHERE id = ? AND valid_until IS NULL",
            (ts, ts, reason or "deprecated", fact_id),
        )

        if cursor.rowcount > 0:
            cursor = conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,))
            row = cursor.fetchone()
            self._log_transaction_sync(
                conn,
                row[0] if row else "unknown",
                "deprecate",
                {"fact_id": fact_id, "reason": reason},
            )
            # CDC: Encole for Neo4j sync (table graph_outbox)
            conn.execute(
                "INSERT INTO graph_outbox (fact_id, action, status) VALUES (?, ?, ?)",
                (fact_id, "deprecate_fact", "pending"),
            )
            conn.commit()
            return True
        return False

    # ─── Recall ─────────────────────────────────────────────────

    def recall_sync(
        self,
        project: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Fact]:
        """Synchronous version of recall."""
        from cortex.engine.query_mixin import _FACT_COLUMNS, _FACT_JOIN

        conn = self._get_sync_conn()
        query = f"""
            SELECT {_FACT_COLUMNS}
            {_FACT_JOIN}
            WHERE f.project = ? AND f.valid_until IS NULL
            ORDER BY (
                f.consensus_score * 0.8
                + (1.0 / (1.0 + (julianday('now') - julianday(f.created_at)))) * 0.2
            ) DESC, f.fact_type, f.created_at DESC
        """
        params: list = [project]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        if offset:
            query += " OFFSET ?"
            params.append(offset)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    def reconstruct_state_sync(
        self,
        target_tx_id: int,
        project: str | None = None,
    ) -> list[Fact]:
        """Synchronous version of reconstruct_state."""
        from cortex.engine.query_mixin import _FACT_COLUMNS, _FACT_JOIN

        conn = self._get_sync_conn()
        cursor = conn.execute(
            "SELECT timestamp FROM transactions WHERE id = ?",
            (target_tx_id,),
        )
        tx = cursor.fetchone()
        if not tx:
            raise ValueError(f"Transaction {target_tx_id} not found")
        tx_time = tx[0]

        query = (
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
            "WHERE (f.created_at <= ? "
            "  AND (f.valid_until IS NULL OR f.valid_until > ?)) "
            "  AND (f.tx_id IS NULL OR f.tx_id <= ?)"
        )
        params: list = [tx_time, tx_time, target_tx_id]
        if project:
            query += " AND f.project = ?"
            params.append(project)
        query += " ORDER BY f.id ASC"
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    # ─── History ────────────────────────────────────────────────

    def history_sync(
        self,
        project: str,
        as_of: str | None = None,
    ) -> list[Fact]:
        """Synchronous version of history."""
        from cortex.engine.query_mixin import _FACT_COLUMNS, _FACT_JOIN
        from cortex.memory.temporal import build_temporal_filter_params

        conn = self._get_sync_conn()
        if as_of:
            clause, params = build_temporal_filter_params(as_of, table_alias="f")
            query = (
                f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
                f"WHERE f.project = ? AND {clause} "
                "ORDER BY f.valid_from DESC"
            )
            cursor = conn.execute(query, [project] + params)
        else:
            query = (
                f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
                "WHERE f.project = ? "
                "ORDER BY f.valid_from DESC"
            )
            cursor = conn.execute(query, (project,))

        rows = cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    # ─── Stats ──────────────────────────────────────────────────

    def stats_sync(self) -> dict:
        """Synchronous version of stats."""
        conn = self._get_sync_conn()

        cursor = conn.execute("SELECT COUNT(*) FROM facts")
        total = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL")
        active = cursor.fetchone()[0]

        cursor = conn.execute("SELECT DISTINCT project FROM facts WHERE valid_until IS NULL")
        projects = [p[0] for p in cursor.fetchall()]

        cursor = conn.execute(
            "SELECT fact_type, COUNT(*) FROM facts WHERE valid_until IS NULL GROUP BY fact_type"
        )
        types = dict(cursor.fetchall())

        cursor = conn.execute("SELECT COUNT(*) FROM transactions")
        tx_count = cursor.fetchone()[0]

        db_size = self._db_path.stat().st_size / (1024 * 1024) if self._db_path.exists() else 0

        try:
            cursor = conn.execute("SELECT COUNT(*) FROM fact_embeddings")
            embeddings = cursor.fetchone()[0]
        except (sqlite3.Error, OSError, ValueError):
            embeddings = 0

        return {
            "total_facts": total,
            "active_facts": active,
            "deprecated_facts": total - active,
            "projects": projects,
            "project_count": len(projects),
            "types": types,
            "transactions": tx_count,
            "embeddings": embeddings,
            "db_path": str(self._db_path),
            "db_size_mb": round(db_size, 2),
        }
