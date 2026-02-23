# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.2 — Sovereign Write Worker (KETER-∞ Metal-Level).

Eliminates SQLite BUSY errors by routing ALL writes through a single
dedicated thread with one persistent connection using BEGIN IMMEDIATE.

Architecture:
    ┌─────────────┐    asyncio.Queue    ┌──────────────────┐
    │ Async Callers├───────────────────►│  _writer_loop()  │
    │ (daemon/CLI) │                    │  (dedicated task) │
    └─────────────┘    Future<Result>   └──────┬───────────┘
                       ◄────────────────────────┘
                                         Single sqlite3
                                         Connection (WAL)

The writer loop processes operations sequentially in-application (RAM),
eliminating lock contention at the SQLite level entirely.

Usage:
    writer = SqliteWriteWorker(db_path)
    await writer.start()

    # Automatic batching via transaction grouping:
    result = await writer.execute(
        "INSERT INTO facts (project, content) VALUES (?, ?)",
        ("cortex", "A new fact")
    )

    # For multi-statement transactions:
    async with writer.transaction() as tx:
        await tx.execute("INSERT INTO ...", params1)
        await tx.execute("UPDATE ...", params2)
        # Auto-commits on exit, auto-rollbacks on exception

    await writer.stop()
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from typing import Any

from cortex.db_messages import (
    TransactionProxy as _TransactionProxy,
)
from cortex.db_messages import (
    _Message,
    _Shutdown,
    _TxBegin,
    _TxCommit,
    _TxRollback,
    _WriteOp,
)
from cortex.result import Err, Ok, Result

__all__ = ["SqliteWriteWorker"]

logger = logging.getLogger("cortex.db.writer")


# ─── Write Worker ─────────────────────────────────────────────────────


class SqliteWriteWorker:
    """Single-writer queue for SQLite.

    All writes are serialized through an asyncio.Queue and processed
    by a single dedicated task holding one persistent connection.
    This eliminates SQLITE_BUSY errors architecturally.
    """

    # Checkpoint WAL every N writes to avoid unbounded WAL growth.
    _CHECKPOINT_INTERVAL: int = 5000

    def __init__(self, db_path: str, *, queue_size: int = 10_000):
        self._db_path = db_path
        self._queue: asyncio.Queue[_Message] = asyncio.Queue(maxsize=queue_size)
        self._task: asyncio.Task[None] | None = None
        self._conn: sqlite3.Connection | None = None
        self._started = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._write_count: int = 0

    @property
    def is_running(self) -> bool:
        return self._started and self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start the writer loop."""
        if self._started:
            return

        self._loop = asyncio.get_running_loop()

        # Create the connection in a thread to not block the event loop
        self._conn = await self._loop.run_in_executor(None, self._create_connection)

        self._task = asyncio.create_task(self._writer_loop(), name="cortex-sqlite-writer")
        self._started = True
        logger.info(
            "SqliteWriteWorker started (db=%s, queue_size=%d)",
            self._db_path,
            self._queue.maxsize,
        )

    def _create_connection(self) -> sqlite3.Connection:
        """Create and configure the single writer connection (runs in executor)."""
        from cortex.db import connect_writer

        conn = connect_writer(self._db_path)
        # Manual transaction control (autocommit mode)
        conn.isolation_level = None
        # Writer-specific performance pragmas
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        logger.debug("Writer connection configured via connect_writer() factory")
        return conn

    async def stop(self) -> None:
        """Gracefully stop the writer loop."""
        if not self._started:
            return

        # Send poison pill
        loop = asyncio.get_running_loop()
        shutdown = _Shutdown(future=loop.create_future())
        await self._queue.put(shutdown)

        # Wait for the writer to process remaining items and exit
        try:
            await asyncio.wait_for(shutdown.future, timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Writer shutdown timed out, cancelling task")
            if self._task:
                self._task.cancel()

        # Final WAL checkpoint before closing
        if self._conn:
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)"),
                )
                logger.debug("Final WAL checkpoint completed on shutdown")
            except sqlite3.Error as e:
                logger.warning("WAL checkpoint on shutdown failed: %s", e)

        # Close connection in executor
        if self._conn:
            await asyncio.get_running_loop().run_in_executor(None, self._conn.close)
            self._conn = None

        self._started = False
        self._write_count = 0
        logger.info("SqliteWriteWorker stopped")

    async def checkpoint(self) -> Result[int, str]:
        """Manual WAL checkpoint. Call during low-activity periods.

        Returns:
            Ok(pages_checkpointed) on success, Err(message) on failure.
        """
        if not self._started or not self._conn:
            return Err("Writer not running")

        loop = asyncio.get_running_loop()
        try:
            cursor = await loop.run_in_executor(
                None,
                lambda: self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)"),
            )
            row = cursor.fetchone()
            pages = row[1] if row else 0
            self._write_count = 0
            logger.debug("WAL checkpoint completed: %d pages", pages)
            return Ok(pages)
        except sqlite3.Error as e:
            return Err(f"WAL checkpoint failed: {e}")

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Result[int, str]:
        """Enqueue a write operation and wait for the result.

        Returns:
            Ok(rowcount) on success, Err(message) on failure.
        """
        if not self._started:
            return Err("SqliteWriteWorker is not running")

        loop = asyncio.get_running_loop()
        op = _WriteOp(sql=sql, params=params, future=loop.create_future())
        await self._queue.put(op)
        return await op.future

    async def execute_many(self, operations: list[tuple[str, tuple[Any, ...]]]) -> Result[int, str]:
        """Execute multiple writes as a single transaction.

        Returns:
            Ok(total_rowcount) on success, Err(message) on failure.
        """
        if not self._started:
            return Err("SqliteWriteWorker is not running")

        loop = asyncio.get_running_loop()

        # Begin
        begin = _TxBegin(future=loop.create_future())
        await self._queue.put(begin)
        result = await begin.future
        if isinstance(result, Err):
            return result

        total_rows = 0
        for sql, params in operations:
            op_result = await self.execute(sql, params)
            if isinstance(op_result, Err):
                # Rollback on error
                rollback = _TxRollback(future=loop.create_future())
                await self._queue.put(rollback)
                await rollback.future
                return op_result
            total_rows += op_result.value

        # Commit
        commit = _TxCommit(future=loop.create_future())
        await self._queue.put(commit)
        commit_result = await commit.future
        if isinstance(commit_result, Err):
            return Err(f"Commit failed: {commit_result.error}")

        return Ok(total_rows)

    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactional writes.

        Usage:
            async with writer.transaction() as tx:
                await tx.execute("INSERT ...", params)
                await tx.execute("UPDATE ...", params)
        """
        loop = asyncio.get_running_loop()

        # Begin transaction
        begin = _TxBegin(future=loop.create_future())
        await self._queue.put(begin)
        result = await begin.future
        if isinstance(result, Err):
            raise RuntimeError(f"Failed to begin transaction: {result.error}")

        proxy = _TransactionProxy(self)
        try:
            yield proxy
            # Commit on clean exit
            commit = _TxCommit(future=loop.create_future())
            await self._queue.put(commit)
            await commit.future
        except BaseException:
            # Rollback on error
            rollback = _TxRollback(future=loop.create_future())
            await self._queue.put(rollback)
            await rollback.future
            raise

    # ─── Internal Writer Loop ─────────────────────────────────────────

    async def _writer_loop(self) -> None:
        """Main writer loop — processes messages sequentially."""
        assert self._conn is not None
        conn = self._conn
        loop = asyncio.get_running_loop()

        logger.debug("Writer loop started, processing queue")

        while True:
            try:
                msg = await self._queue.get()
            except asyncio.CancelledError:
                raise  # Re-raise to allow proper task cancellation

            try:
                should_exit = await self._dispatch_message(msg, conn, loop)
                if should_exit:
                    break
            except (sqlite3.Error, RuntimeError) as e:
                logger.exception("Unexpected error in writer loop: %s", e)

        logger.debug("Writer loop exited")

    async def _dispatch_message(
        self,
        msg: _Message,
        conn: sqlite3.Connection,
        loop: asyncio.AbstractEventLoop,
    ) -> bool:
        """Dispatch a single message. Returns True if loop should exit."""
        match msg:
            case _Shutdown(future=fut):
                await self._handle_shutdown(conn, loop, fut)
                return True
            case _WriteOp() as op:
                await self._process_write(conn, op, loop)
            case _TxBegin(future=fut):
                await self._handle_tx_sql(conn, loop, fut, "BEGIN IMMEDIATE")
            case _TxCommit(future=fut):
                await self._handle_tx_sql(conn, loop, fut, "COMMIT")
            case _TxRollback(future=fut):
                await self._handle_tx_sql(conn, loop, fut, "ROLLBACK")
        return False

    async def _handle_shutdown(
        self,
        conn: sqlite3.Connection,
        loop: asyncio.AbstractEventLoop,
        fut: asyncio.Future,
    ) -> None:
        """Drain remaining writes and signal shutdown complete."""
        while not self._queue.empty():
            remaining = self._queue.get_nowait()
            if isinstance(remaining, _WriteOp):
                await self._process_write(conn, remaining, loop)
        loop.call_soon_threadsafe(fut.set_result, Ok(None))

    async def _handle_tx_sql(
        self,
        conn: sqlite3.Connection,
        loop: asyncio.AbstractEventLoop,
        fut: asyncio.Future,
        sql: str,
    ) -> None:
        """Execute a transaction control statement (BEGIN/COMMIT/ROLLBACK)."""
        try:
            await loop.run_in_executor(None, conn.execute, sql)
            loop.call_soon_threadsafe(fut.set_result, Ok(None))
        except sqlite3.Error as e:
            if sql == "ROLLBACK":
                logger.error("ROLLBACK failed: %s", e)
            loop.call_soon_threadsafe(fut.set_result, Err(f"{sql} failed: {e}"))

    async def _process_write(
        self,
        conn: sqlite3.Connection,
        op: _WriteOp,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Process a single write operation in the executor."""
        try:
            cursor = await loop.run_in_executor(None, lambda: conn.execute(op.sql, op.params))
            # Auto-commit if not inside an explicit transaction
            if not conn.in_transaction:
                await loop.run_in_executor(None, conn.commit)
            loop.call_soon_threadsafe(op.future.set_result, Ok(cursor.rowcount))

            # Periodic WAL checkpoint to prevent unbounded WAL growth
            self._write_count += 1
            if self._write_count >= self._CHECKPOINT_INTERVAL:
                try:
                    await loop.run_in_executor(
                        None, lambda: conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                    )
                    self._write_count = 0
                    logger.debug("Periodic WAL checkpoint at %d writes", self._CHECKPOINT_INTERVAL)
                except sqlite3.Error:
                    pass  # Non-critical: checkpoint will retry next interval

        except sqlite3.Error as e:
            logger.warning("Write failed: %s | SQL: %s", e, op.sql[:100])
            loop.call_soon_threadsafe(
                op.future.set_result,
                Err(f"SQLite write error: {e}"),
            )
