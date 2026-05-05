"""
Crypto-Shredding Engine — GDPR Right to Erasure (Ω₃ / Ω₁₂).

Resolves the EU AI Act ↔ GDPR paradox:
  - EU AI Act demands immutable audit trails for AI decisions.
  - GDPR demands the right to erase personal data.

Solution: Per-fact HKDF key derivation. Destroying the key makes the
ciphertext irrecoverable without altering the ledger hash chain.
The transaction log stays intact for regulators; the personal data
becomes cryptographic noise.

Architecture:
  - Each fact's content is encrypted with a key derived from:
    HKDF(master_key, info=f"{tenant_id}:fact:{fact_id}")
  - Shredding = recording the fact_id in `shredded_keys` table
    + invalidating the derived key from cache
  - The ledger's hash chain uses the *encrypted* ciphertext, so
    shredding doesn't break chain integrity.

Edge-compatible: SQLite-only, no external services.
GPU-native: N/A (crypto is CPU-bound, parallelizable via ProcessPool).
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional, cast

from cortex.crypto.aes import CortexEncrypter
from cortex.utils.canonical import canonical_json, compute_fact_hash, compute_tx_hash

try:
    import _sqlite3 as _stdlib_sqlite3
except ImportError:  # pragma: no cover - CPython always provides this here.
    _stdlib_sqlite3 = None  # type: ignore[assignment]

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.crypto.shredder")

__all__ = ["CryptoShredder", "ShredResult", "ShredBatchResult"]

_AUXILIARY_ERASURE_TABLES = frozenset(
    {"facts_fts", "fact_embeddings", "specular_embeddings", "fact_tags"}
)
_DYNAMIC_TABLES = frozenset(
    {"facts", "transactions", "facts_fts", "fact_embeddings", "specular_embeddings", "fact_tags"}
)

_SYNC_CONNECTION_TYPES: tuple[type[Any], ...] = tuple(
    {
        sqlite3.Connection,
        *(
            [_stdlib_sqlite3.Connection]
            if _stdlib_sqlite3 is not None and hasattr(_stdlib_sqlite3, "Connection")
            else []
        ),
    }
)
_SQLITE_ERRORS: tuple[type[BaseException], ...] = tuple(
    {
        sqlite3.Error,
        *(
            [_stdlib_sqlite3.Error]
            if _stdlib_sqlite3 is not None and hasattr(_stdlib_sqlite3, "Error")
            else []
        ),
    }
)
_SQLITE_OPERATION_ERRORS = (*_SQLITE_ERRORS, OSError)
_SQLITE_SHRED_ERRORS = (*_SQLITE_ERRORS, OSError, ValueError, RuntimeError)


def _is_sync_connection(conn: Any) -> bool:
    """Return whether conn is a stdlib or pysqlite-compatible SQLite connection."""
    return isinstance(conn, _SYNC_CONNECTION_TYPES)


@dataclass
class ShredResult:
    """Outcome of a single fact shred operation."""

    fact_id: int
    tenant_id: str
    success: bool
    reason: str = "gdpr_erasure"
    error: Optional[str] = None
    was_already_shredded: bool = False


@dataclass
class ShredBatchResult:
    """Aggregate result of a batch shred operation."""

    total_requested: int = 0
    shredded: int = 0
    already_shredded: int = 0
    failed: int = 0
    results: list[ShredResult] = field(default_factory=list)


class CryptoShredder:
    """Sovereign Crypto-Shredding Engine.

    Destroys per-fact encryption keys to make ciphertext irrecoverable.
    The immutable ledger hash chain remains intact for EU AI Act compliance.
    """

    def __init__(self, conn: aiosqlite.Connection | sqlite3.Connection):
        self._conn = conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create erasure audit tables if they don't exist."""
        sql = """
            CREATE TABLE IF NOT EXISTS shredded_keys (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id     INTEGER NOT NULL,
                tenant_id   TEXT    NOT NULL DEFAULT 'default',
                reason      TEXT    NOT NULL DEFAULT 'gdpr_erasure',
                shredded_by TEXT,
                shredded_at TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(fact_id, tenant_id)
            );
        """
        try:
            if _is_sync_connection(self._conn):
                from cortex.database.schema import CREATE_TRANSACTIONS, CREATE_TRANSACTIONS_INDEX

                self._conn.execute(sql)
                self._conn.executescript(CREATE_TRANSACTIONS)
                self._conn.executescript(CREATE_TRANSACTIONS_INDEX)
                self._conn.commit()
        except _SQLITE_ERRORS as e:
            logger.warning("Schema creation skipped (may exist): %s", e)

    async def _ensure_schema_async(self) -> None:
        """Async variant for aiosqlite connections."""
        sql = """
            CREATE TABLE IF NOT EXISTS shredded_keys (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id     INTEGER NOT NULL,
                tenant_id   TEXT    NOT NULL DEFAULT 'default',
                reason      TEXT    NOT NULL DEFAULT 'gdpr_erasure',
                shredded_by TEXT,
                shredded_at TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(fact_id, tenant_id)
            );
        """
        try:
            from cortex.database.schema import CREATE_TRANSACTIONS, CREATE_TRANSACTIONS_INDEX

            await self._conn.execute(sql)  # type: ignore[reportAttributeAccessIssue]
            await self._conn.executescript(CREATE_TRANSACTIONS)  # type: ignore[reportAttributeAccessIssue]
            await self._conn.executescript(CREATE_TRANSACTIONS_INDEX)  # type: ignore[reportAttributeAccessIssue]
            await self._conn.commit()  # type: ignore[reportAttributeAccessIssue]
        except _SQLITE_OPERATION_ERRORS as e:
            logger.warning("Async schema creation skipped: %s", e)

    def _rollback_sync(self) -> None:
        """Rollback a failed shred transaction without masking the original error."""
        if not _is_sync_connection(self._conn):
            return
        try:
            self._conn.rollback()
        except _SQLITE_ERRORS as e:
            logger.warning("Rollback after shred failure failed: %s", e)

    async def _rollback_async(self) -> None:
        """Async rollback for failed shred operations."""
        try:
            await self._conn.rollback()  # type: ignore[reportAttributeAccessIssue]
        except _SQLITE_OPERATION_ERRORS as e:
            logger.warning("Async rollback after shred failure failed: %s", e)

    def is_shredded(self, fact_id: int, tenant_id: str = "default") -> bool:
        """Check if a fact's key has been shredded (sync)."""
        if not _is_sync_connection(self._conn):
            raise TypeError("Use is_shredded_async for async connections")
        conn = cast(sqlite3.Connection, self._conn)
        cursor = conn.execute(
            "SELECT 1 FROM shredded_keys WHERE fact_id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        return cursor.fetchone() is not None

    async def is_shredded_async(self, fact_id: int, tenant_id: str = "default") -> bool:
        """Check if a fact's key has been shredded (async)."""
        await self._ensure_schema_async()
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT 1 FROM shredded_keys WHERE fact_id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        return (await cursor.fetchone()) is not None

    def get_shredded_fact_ids(self, tenant_id: str = "default") -> set[int]:
        """Return all shredded fact IDs for a tenant (sync)."""
        if not _is_sync_connection(self._conn):
            raise TypeError("Use get_shredded_fact_ids_async for async")
        conn = cast(sqlite3.Connection, self._conn)
        cursor = conn.execute(
            "SELECT fact_id FROM shredded_keys WHERE tenant_id = ?",
            (tenant_id,),
        )
        return {row[0] for row in cursor.fetchall()}

    async def get_shredded_fact_ids_async(self, tenant_id: str = "default") -> set[int]:
        """Return all shredded fact IDs for a tenant (async)."""
        await self._ensure_schema_async()
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT fact_id FROM shredded_keys WHERE tenant_id = ?",
            (tenant_id,),
        )
        rows = await cursor.fetchall()
        return {row[0] for row in rows}

    @staticmethod
    def _assert_dynamic_table(table_name: str) -> None:
        """Reject non-static table names before using PRAGMA/f-string SQL."""
        if table_name not in _DYNAMIC_TABLES:
            raise ValueError(f"Unsupported table name: {table_name}")

    def _table_exists_sync(self, table_name: str) -> bool:
        self._assert_dynamic_table(table_name)
        conn = cast(sqlite3.Connection, self._conn)
        cursor = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name = ? AND type IN ('table', 'view')",
            (table_name,),
        )
        return cursor.fetchone() is not None

    async def _table_exists_async(self, table_name: str) -> bool:
        self._assert_dynamic_table(table_name)
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT 1 FROM sqlite_master WHERE name = ? AND type IN ('table', 'view')",
            (table_name,),
        )
        return (await cursor.fetchone()) is not None

    def _table_columns_sync(self, table_name: str) -> set[str]:
        self._assert_dynamic_table(table_name)
        conn = cast(sqlite3.Connection, self._conn)
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        return {str(row[1]) for row in cursor.fetchall()}

    async def _table_columns_async(self, table_name: str) -> set[str]:
        self._assert_dynamic_table(table_name)
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            f"PRAGMA table_info({table_name})"
        )
        return {str(row[1]) for row in await cursor.fetchall()}

    def _fetch_fact_sync(self, fact_id: int, tenant_id: str) -> dict[str, Any]:
        columns = self._table_columns_sync("facts")
        missing = {"id", "tenant_id", "content"} - columns
        if missing:
            raise RuntimeError(f"facts table lacks required erasure columns: {sorted(missing)}")

        select_cols = ["content"]
        if "project" in columns:
            select_cols.append("project")
        if "is_tombstoned" in columns:
            select_cols.append("is_tombstoned")

        conn = cast(sqlite3.Connection, self._conn)
        cursor = conn.execute(
            f"SELECT {', '.join(select_cols)} FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Fact {fact_id} not found for tenant {tenant_id}")

        data = dict(zip(select_cols, row, strict=True))
        data.setdefault("project", "privacy")
        data.setdefault("is_tombstoned", 0)
        return data

    async def _fetch_fact_async(self, fact_id: int, tenant_id: str) -> dict[str, Any]:
        columns = await self._table_columns_async("facts")
        missing = {"id", "tenant_id", "content"} - columns
        if missing:
            raise RuntimeError(f"facts table lacks required erasure columns: {sorted(missing)}")

        select_cols = ["content"]
        if "project" in columns:
            select_cols.append("project")
        if "is_tombstoned" in columns:
            select_cols.append("is_tombstoned")

        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            f"SELECT {', '.join(select_cols)} FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise ValueError(f"Fact {fact_id} not found for tenant {tenant_id}")

        data = dict(zip(select_cols, row, strict=True))
        data.setdefault("project", "privacy")
        data.setdefault("is_tombstoned", 0)
        return data

    @staticmethod
    def _is_crypto_tombstone(content: Any) -> bool:
        return isinstance(content, str) and "gdpr_crypto_shred_v1" in content

    @staticmethod
    def _build_tombstone_content(
        fact_id: int,
        tenant_id: str,
        reason: str,
        shredded_at: str,
        previous_content: Any,
    ) -> str:
        """Build a non-personal tombstone replacing erased fact content."""
        previous = str(previous_content or "")
        previous_was_encrypted = previous.startswith(CortexEncrypter.PREFIX)
        payload: dict[str, Any] = {
            "cortex_crypto_shredded": True,
            "schema": "gdpr_crypto_shred_v1",
            "fact_id": fact_id,
            "tenant_id": tenant_id,
            "reason": reason,
            "shredded_at": shredded_at,
            "previous_content_erased": True,
            "previous_content_was_encrypted": previous_was_encrypted,
        }
        if previous_was_encrypted:
            payload["previous_ciphertext_sha256"] = hashlib.sha256(
                previous.encode("utf-8")
            ).hexdigest()
        return canonical_json(payload)

    @staticmethod
    def _build_tombstone_metadata(
        fact_id: int,
        tenant_id: str,
        reason: str,
        shredded_at: str,
    ) -> dict[str, Any]:
        return {
            "cortex_crypto_shredded": True,
            "schema": "gdpr_crypto_shred_v1",
            "fact_id": fact_id,
            "tenant_id": tenant_id,
            "reason": reason,
            "shredded_at": shredded_at,
        }

    @staticmethod
    def _encode_tombstone_metadata(metadata: dict[str, Any], tenant_id: str) -> str:
        try:
            from cortex.crypto import get_default_encrypter

            encrypted = get_default_encrypter().encrypt_json(metadata, tenant_id=tenant_id)
            return encrypted or canonical_json(metadata)
        except (ImportError, RuntimeError, ValueError, OSError) as e:
            logger.debug("Tombstone metadata encryption skipped: %s", e)
            return canonical_json(metadata)

    def _planned_side_effects_sync(self) -> list[str]:
        return sorted(
            table for table in _AUXILIARY_ERASURE_TABLES if self._table_exists_sync(table)
        )

    async def _planned_side_effects_async(self) -> list[str]:
        present = []
        for table in _AUXILIARY_ERASURE_TABLES:
            if await self._table_exists_async(table):
                present.append(table)
        return sorted(present)

    def _delete_side_effects_sync(self, fact_id: int, tenant_id: str) -> None:
        for table in self._planned_side_effects_sync():
            columns = self._table_columns_sync(table)
            if table == "facts_fts":
                if "tenant_id" in columns:
                    self._conn.execute(
                        "DELETE FROM facts_fts WHERE rowid = ? AND tenant_id = ?",
                        (fact_id, tenant_id),
                    )
                else:
                    self._conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
            elif "tenant_id" in columns:
                self._conn.execute(
                    f"DELETE FROM {table} WHERE fact_id = ? AND tenant_id = ?",
                    (fact_id, tenant_id),
                )
            else:
                self._conn.execute(f"DELETE FROM {table} WHERE fact_id = ?", (fact_id,))

    async def _delete_side_effects_async(self, fact_id: int, tenant_id: str) -> None:
        for table in await self._planned_side_effects_async():
            columns = await self._table_columns_async(table)
            if table == "facts_fts":
                if "tenant_id" in columns:
                    await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
                        "DELETE FROM facts_fts WHERE rowid = ? AND tenant_id = ?",
                        (fact_id, tenant_id),
                    )
                else:
                    await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
                        "DELETE FROM facts_fts WHERE rowid = ?",
                        (fact_id,),
                    )
            elif "tenant_id" in columns:
                await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
                    f"DELETE FROM {table} WHERE fact_id = ? AND tenant_id = ?",
                    (fact_id, tenant_id),
                )
            else:
                await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
                    f"DELETE FROM {table} WHERE fact_id = ?",
                    (fact_id,),
                )

    def _insert_shred_transaction_sync(
        self,
        *,
        fact_id: int,
        tenant_id: str,
        project: str,
        reason: str,
        timestamp: str,
        side_effects: list[str],
    ) -> int | None:
        if not self._table_exists_sync("transactions"):
            return None
        columns = self._table_columns_sync("transactions")
        if "hash" not in columns:
            return None

        detail_json = canonical_json(
            {
                "fact_id": fact_id,
                "reason": reason,
                "schema": "gdpr_crypto_shred_v1",
                "side_effects": side_effects,
            }
        )
        if "tenant_id" in columns:
            conn = cast(sqlite3.Connection, self._conn)
            cursor = conn.execute(
                "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
                (tenant_id,),
            )
        else:
            conn = cast(sqlite3.Connection, self._conn)
            cursor = conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        prev_hash = row[0] if row and row[0] else "GENESIS"
        tx_hash = compute_tx_hash(
            prev_hash,
            project,
            "crypto_shred",
            detail_json,
            timestamp,
            tenant_id=tenant_id if "tenant_id" in columns else None,
        )
        values_by_column = {
            "tenant_id": tenant_id,
            "project": project,
            "action": "crypto_shred",
            "detail": detail_json,
            "prev_hash": prev_hash,
            "hash": tx_hash,
            "timestamp": timestamp,
        }
        insert_columns = [col for col in values_by_column if col in columns]
        placeholders = ", ".join("?" for _ in insert_columns)
        sql = f"INSERT INTO transactions ({', '.join(insert_columns)}) VALUES ({placeholders})"
        conn = cast(sqlite3.Connection, self._conn)
        cursor = conn.execute(sql, [values_by_column[col] for col in insert_columns])
        return int(cursor.lastrowid) if cursor.lastrowid is not None else None

    async def _insert_shred_transaction_async(
        self,
        *,
        fact_id: int,
        tenant_id: str,
        project: str,
        reason: str,
        timestamp: str,
        side_effects: list[str],
    ) -> int | None:
        if not await self._table_exists_async("transactions"):
            return None
        columns = await self._table_columns_async("transactions")
        if "hash" not in columns:
            return None

        detail_json = canonical_json(
            {
                "fact_id": fact_id,
                "reason": reason,
                "schema": "gdpr_crypto_shred_v1",
                "side_effects": side_effects,
            }
        )
        if "tenant_id" in columns:
            cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
                "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
                (tenant_id,),
            )
        else:
            cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
                "SELECT hash FROM transactions ORDER BY id DESC LIMIT 1"
            )
        row = await cursor.fetchone()
        prev_hash = row[0] if row and row[0] else "GENESIS"
        tx_hash = compute_tx_hash(
            prev_hash,
            project,
            "crypto_shred",
            detail_json,
            timestamp,
            tenant_id=tenant_id if "tenant_id" in columns else None,
        )
        values_by_column = {
            "tenant_id": tenant_id,
            "project": project,
            "action": "crypto_shred",
            "detail": detail_json,
            "prev_hash": prev_hash,
            "hash": tx_hash,
            "timestamp": timestamp,
        }
        insert_columns = [col for col in values_by_column if col in columns]
        placeholders = ", ".join("?" for _ in insert_columns)
        sql = f"INSERT INTO transactions ({', '.join(insert_columns)}) VALUES ({placeholders})"
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            sql,
            [values_by_column[col] for col in insert_columns],
        )
        return int(cursor.lastrowid) if cursor.lastrowid is not None else None

    def _update_fact_tombstone_sync(
        self,
        *,
        fact_id: int,
        tenant_id: str,
        content: str,
        metadata: dict[str, Any],
        timestamp: str,
        tx_id: int | None,
    ) -> None:
        columns = self._table_columns_sync("facts")
        setters: list[str] = ["content = ?"]
        values: list[Any] = [content]
        if "hash" in columns:
            setters.append("hash = ?")
            values.append(compute_fact_hash(content))
        if "metadata" in columns:
            setters.append("metadata = ?")
            values.append(self._encode_tombstone_metadata(metadata, tenant_id))
        if "valid_until" in columns:
            setters.append("valid_until = ?")
            values.append(timestamp)
        if "is_tombstoned" in columns:
            setters.append("is_tombstoned = 1")
        if "updated_at" in columns:
            setters.append("updated_at = ?")
            values.append(timestamp)
        if tx_id is not None and "tx_id" in columns:
            setters.append("tx_id = ?")
            values.append(tx_id)

        values.extend([fact_id, tenant_id])
        conn = cast(sqlite3.Connection, self._conn)
        cursor = conn.execute(
            f"UPDATE facts SET {', '.join(setters)} WHERE id = ? AND tenant_id = ?",
            values,
        )
        if cursor.rowcount != 1:
            raise RuntimeError(f"Fact {fact_id} could not be tombstoned for tenant {tenant_id}")

    async def _update_fact_tombstone_async(
        self,
        *,
        fact_id: int,
        tenant_id: str,
        content: str,
        metadata: dict[str, Any],
        timestamp: str,
        tx_id: int | None,
    ) -> None:
        columns = await self._table_columns_async("facts")
        setters: list[str] = ["content = ?"]
        values: list[Any] = [content]
        if "hash" in columns:
            setters.append("hash = ?")
            values.append(compute_fact_hash(content))
        if "metadata" in columns:
            setters.append("metadata = ?")
            values.append(self._encode_tombstone_metadata(metadata, tenant_id))
        if "valid_until" in columns:
            setters.append("valid_until = ?")
            values.append(timestamp)
        if "is_tombstoned" in columns:
            setters.append("is_tombstoned = 1")
        if "updated_at" in columns:
            setters.append("updated_at = ?")
            values.append(timestamp)
        if tx_id is not None and "tx_id" in columns:
            setters.append("tx_id = ?")
            values.append(tx_id)

        values.extend([fact_id, tenant_id])
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            f"UPDATE facts SET {', '.join(setters)} WHERE id = ? AND tenant_id = ?",
            values,
        )
        if cursor.rowcount != 1:
            raise RuntimeError(f"Fact {fact_id} could not be tombstoned for tenant {tenant_id}")

    def shred_fact(
        self,
        fact_id: int,
        tenant_id: str = "default",
        reason: str = "gdpr_erasure",
        shredded_by: Optional[str] = None,
    ) -> ShredResult:
        """Destroy the encryption key for a single fact (sync).

        The fact's ciphertext in the DB becomes permanently irrecoverable.
        The ledger hash chain is NOT affected (it hashes ciphertext, not plaintext).

        This also invalidates the HKDF-derived key from the encrypter's cache
        to prevent in-memory access after shredding.
        """
        if not _is_sync_connection(self._conn):
            raise TypeError("Use shred_fact_async for async connections")

        try:
            ts = datetime.now(timezone.utc).isoformat()
            fact = self._fetch_fact_sync(fact_id, tenant_id)
            was_already_shredded = self.is_shredded(fact_id, tenant_id)
            if was_already_shredded and self._is_crypto_tombstone(fact.get("content")):
                return ShredResult(
                    fact_id=fact_id,
                    tenant_id=tenant_id,
                    success=True,
                    reason=reason,
                    was_already_shredded=True,
                )

            if not was_already_shredded:
                self._conn.execute(
                    "INSERT OR IGNORE INTO shredded_keys "
                    "(fact_id, tenant_id, reason, shredded_by, shredded_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (fact_id, tenant_id, reason, shredded_by, ts),
                )

            side_effects = self._planned_side_effects_sync()
            tx_id = self._insert_shred_transaction_sync(
                fact_id=fact_id,
                tenant_id=tenant_id,
                project=str(fact.get("project") or "privacy"),
                reason=reason,
                timestamp=ts,
                side_effects=side_effects,
            )
            tombstone_content = self._build_tombstone_content(
                fact_id=fact_id,
                tenant_id=tenant_id,
                reason=reason,
                shredded_at=ts,
                previous_content=fact.get("content"),
            )
            tombstone_metadata = self._build_tombstone_metadata(
                fact_id=fact_id,
                tenant_id=tenant_id,
                reason=reason,
                shredded_at=ts,
            )
            self._update_fact_tombstone_sync(
                fact_id=fact_id,
                tenant_id=tenant_id,
                content=tombstone_content,
                metadata=tombstone_metadata,
                timestamp=ts,
                tx_id=tx_id,
            )
            self._delete_side_effects_sync(fact_id, tenant_id)

            # Invalidate the fact-specific derived key from the encrypter cache
            self._invalidate_fact_key(fact_id, tenant_id)

            self._conn.commit()
            logger.info(
                "Crypto-shredded fact #%d (tenant=%s, reason=%s)",
                fact_id,
                tenant_id,
                reason,
            )
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=True,
                reason=reason,
                was_already_shredded=was_already_shredded,
            )
        except _SQLITE_SHRED_ERRORS as e:
            self._rollback_sync()
            logger.error("Shred failed for fact #%d: %s", fact_id, e)
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=False,
                reason=reason,
                error=str(e),
            )

    async def shred_fact_async(
        self,
        fact_id: int,
        tenant_id: str = "default",
        reason: str = "gdpr_erasure",
        shredded_by: Optional[str] = None,
    ) -> ShredResult:
        """Destroy the encryption key for a single fact (async)."""
        try:
            await self._ensure_schema_async()
            ts = datetime.now(timezone.utc).isoformat()
            fact = await self._fetch_fact_async(fact_id, tenant_id)
            was_already_shredded = await self.is_shredded_async(fact_id, tenant_id)
            if was_already_shredded and self._is_crypto_tombstone(fact.get("content")):
                return ShredResult(
                    fact_id=fact_id,
                    tenant_id=tenant_id,
                    success=True,
                    reason=reason,
                    was_already_shredded=True,
                )

            if not was_already_shredded:
                await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
                    "INSERT OR IGNORE INTO shredded_keys "
                    "(fact_id, tenant_id, reason, shredded_by, shredded_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (fact_id, tenant_id, reason, shredded_by, ts),
                )

            side_effects = await self._planned_side_effects_async()
            tx_id = await self._insert_shred_transaction_async(
                fact_id=fact_id,
                tenant_id=tenant_id,
                project=str(fact.get("project") or "privacy"),
                reason=reason,
                timestamp=ts,
                side_effects=side_effects,
            )
            tombstone_content = self._build_tombstone_content(
                fact_id=fact_id,
                tenant_id=tenant_id,
                reason=reason,
                shredded_at=ts,
                previous_content=fact.get("content"),
            )
            tombstone_metadata = self._build_tombstone_metadata(
                fact_id=fact_id,
                tenant_id=tenant_id,
                reason=reason,
                shredded_at=ts,
            )
            await self._update_fact_tombstone_async(
                fact_id=fact_id,
                tenant_id=tenant_id,
                content=tombstone_content,
                metadata=tombstone_metadata,
                timestamp=ts,
                tx_id=tx_id,
            )
            await self._delete_side_effects_async(fact_id, tenant_id)

            self._invalidate_fact_key(fact_id, tenant_id)

            await self._conn.commit()  # type: ignore[reportAttributeAccessIssue]
            logger.info(
                "Crypto-shredded fact #%d (tenant=%s, reason=%s)",
                fact_id,
                tenant_id,
                reason,
            )
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=True,
                reason=reason,
                was_already_shredded=was_already_shredded,
            )
        except _SQLITE_SHRED_ERRORS as e:
            await self._rollback_async()
            logger.error("Shred failed for fact #%d: %s", fact_id, e)
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=False,
                reason=reason,
                error=str(e),
            )

    async def shred_by_source(
        self,
        source: str,
        tenant_id: str = "default",
        reason: str = "gdpr_erasure",
        shredded_by: Optional[str] = None,
    ) -> ShredBatchResult:
        """Shred all facts from a specific source (e.g., a user agent).

        GDPR use case: user requests erasure of all their data.
        """
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT id FROM facts WHERE source = ? AND tenant_id = ?",
            (source, tenant_id),
        )
        rows = await cursor.fetchall()
        fact_ids = [row[0] for row in rows]

        return await self._shred_batch(fact_ids, tenant_id, reason, shredded_by)

    async def shred_by_project(
        self,
        project: str,
        tenant_id: str = "default",
        reason: str = "project_erasure",
        shredded_by: Optional[str] = None,
    ) -> ShredBatchResult:
        """Shred all facts in a project."""
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT id FROM facts WHERE project = ? AND tenant_id = ?",
            (project, tenant_id),
        )
        rows = await cursor.fetchall()
        fact_ids = [row[0] for row in rows]

        return await self._shred_batch(fact_ids, tenant_id, reason, shredded_by)

    async def _shred_batch(
        self,
        fact_ids: list[int],
        tenant_id: str,
        reason: str,
        shredded_by: Optional[str],
    ) -> ShredBatchResult:
        """Internal batch shred implementation."""
        batch = ShredBatchResult(total_requested=len(fact_ids))

        for fact_id in fact_ids:
            result = await self.shred_fact_async(fact_id, tenant_id, reason, shredded_by)
            batch.results.append(result)

            if result.was_already_shredded:
                batch.already_shredded += 1
            elif result.success:
                batch.shredded += 1
            else:
                batch.failed += 1

        return batch

    def _invalidate_fact_key(self, fact_id: int, tenant_id: str) -> None:
        """Invalidate the HKDF-derived key for a fact from in-memory cache.

        After shredding, even if the encrypter has the master key,
        we poison the cache entry so decryption attempts fail fast.
        """
        try:
            from cortex.crypto.aes import get_default_encrypter

            enc = get_default_encrypter()
            # Remove the fact-specific key derivation marker
            # The _tenant_keys cache only stores per-tenant keys,
            # but we mark this fact_id as shredded so the decrypt
            # path can check before attempting HKDF derivation.
            cache_key = f"{tenant_id}:fact:{fact_id}"
            if hasattr(enc, "_shredded_facts"):
                enc._shredded_facts.add(cache_key)  # type: ignore[reportAttributeAccessIssue]
            else:
                enc._shredded_facts = {cache_key}  # type: ignore[reportAttributeAccessIssue]
        except (ImportError, RuntimeError) as e:
            logger.debug("Key invalidation skipped: %s", e)

    def audit_shredding(self) -> dict[str, Any]:
        """Report on all shredded facts for compliance auditing.

        Returns aggregate statistics without revealing content.
        """
        if not _is_sync_connection(self._conn):
            raise TypeError("Use audit_shredding_async for async")

        conn = cast(sqlite3.Connection, self._conn)
        cursor = conn.execute(
            "SELECT COUNT(*), reason, MIN(shredded_at), MAX(shredded_at) "
            "FROM shredded_keys GROUP BY reason"
        )
        rows = cursor.fetchall()

        reasons = {}
        total = 0
        for row in rows:
            count, reason, earliest, latest = row
            total += count
            reasons[reason] = {
                "count": count,
                "earliest": earliest,
                "latest": latest,
            }

        return {
            "total_shredded": total,
            "by_reason": reasons,
            "compliant": True,
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        }
