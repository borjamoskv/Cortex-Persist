# [C5-REAL] Exergy-Maximized
"""Thread-isolated async SQLite engine (MOSKV-1 APEX Kernel).

Spins up a single dedicated background thread with a synchronous sqlite3 connection,
passing commands via queue and returning results to the asyncio event loop using Futures.
This avoids concurrent access issues and ensures optimal WAL performance under concurrency.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import sqlite3
import threading
from collections.abc import Iterator, Sequence
from typing import Any

logger = logging.getLogger("cortex.database.sovereign_db")

# Import the unpatched connect function to bypass runtime connect block
try:
    from cortex.database.core import _original_sqlite3_connect as _sqlite_connect
except ImportError:
    _sqlite_connect = sqlite3.connect


class SovereignCursor:
    """A thread-safe cursor-like container returned by SovereignDB execution."""

    def __init__(
        self,
        rows: list[tuple[Any, ...]],
        lastrowid: int | None,
        rowcount: int,
        description: tuple[tuple[str, Any, Any, Any, Any, Any, Any], ...] | None,
    ) -> None:
        self._rows = rows
        self._lastrowid = lastrowid
        self._rowcount = rowcount
        self._description = description
        self._iter = iter(rows)

    @property
    def lastrowid(self) -> int | None:
        """Return the last inserted row ID."""
        return self._lastrowid

    @property
    def rowcount(self) -> int:
        """Return the number of affected rows."""
        return self._rowcount

    @property
    def description(self) -> tuple[tuple[str, Any, Any, Any, Any, Any, Any], ...] | None:
        """Return cursor description metadata."""
        return self._description

    def fetchall(self) -> list[tuple[Any, ...]]:
        """Fetch all remaining rows."""
        return self._rows

    def fetchone(self) -> tuple[Any, ...] | None:
        """Fetch the next row."""
        try:
            return next(self._iter)
        except StopIteration:
            return None

    def __iter__(self) -> Iterator[tuple[Any, ...]]:
        return iter(self._rows)

    def __aiter__(self) -> Any:
        class AsyncIter:
            def __init__(self, rows: list[tuple[Any, ...]]) -> None:
                self._iter = iter(rows)

            async def __anext__(self) -> tuple[Any, ...]:
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration from None

        return AsyncIter(self._rows)


class SovereignDB:
    """Thread-isolated SQLite engine for async workflows."""

    def __init__(self, database_path: str, isolation_level: Any = "DEFERRED") -> None:
        """Initialize SovereignDB and start the background worker thread.

        Args:
            database_path: Path to the SQLite database file.
            isolation_level: Transaction isolation level passed to sqlite3.connect.
        """
        self.database_path = database_path
        self.isolation_level = isolation_level

        self._queue: queue.Queue[tuple[Any, ...]] = queue.Queue()
        self._init_event = threading.Event()
        self._init_error: Exception | None = None
        self._conn: sqlite3.Connection | None = None
        self._running = True

        self._thread = threading.Thread(
            target=self._worker_loop,
            name=f"sovereign-db-{id(self)}",
            daemon=True,
        )
        self._thread.start()

    def _worker_loop(self) -> None:
        """Background thread target that manages the sqlite3 connection and task execution."""
        conn = None
        try:
            # 2. Synchronous sqlite3 connection setup
            conn = _sqlite_connect(
                self.database_path,
                isolation_level=self.isolation_level,
                check_same_thread=True,
            )

            # 4. Set performance-optimized PRAGMAs
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")

            self._conn = conn
            self._init_event.set()
        except Exception as e:
            logger.error("Failed to initialize SovereignDB background connection: %s", e)
            self._init_error = e
            self._init_event.set()
            if conn:
                try:
                    conn.close()
                except (ValueError, TypeError, OSError, KeyError):
                    pass
            self._running = False
            self._drain_queue_with_error(e)
            return

        while True:
            try:
                task = self._queue.get()
            except (ValueError, TypeError, OSError, KeyError):
                break

            op = task[0]

            if op == "shutdown":
                future, loop = task[1], task[2]
                try:
                    if self._conn:
                        self._conn.close()
                        self._conn = None
                    loop.call_soon_threadsafe(future.set_result, None)
                except (ValueError, TypeError, OSError, KeyError) as e:
                    loop.call_soon_threadsafe(future.set_exception, e)
                finally:
                    self._queue.task_done()
                break

            # Standard database commands
            op, *args, future, loop = task
            try:
                if not self._conn:
                    raise sqlite3.ProgrammingError("Connection is closed.")

                if op == "execute":
                    sql, parameters = args
                    cursor = self._conn.cursor()
                    if parameters is not None:
                        cursor.execute(sql, parameters)
                    else:
                        cursor.execute(sql)

                    rows = cursor.fetchall()
                    lastrowid = cursor.lastrowid
                    rowcount = cursor.rowcount
                    description = cursor.description
                    cursor.close()

                    result = SovereignCursor(rows, lastrowid, rowcount, description)
                    loop.call_soon_threadsafe(future.set_result, result)

                elif op == "execute_many":
                    sql, seq_of_parameters = args
                    cursor = self._conn.cursor()
                    cursor.executemany(sql, seq_of_parameters)
                    lastrowid = cursor.lastrowid
                    rowcount = cursor.rowcount
                    description = cursor.description
                    cursor.close()

                    result = SovereignCursor([], lastrowid, rowcount, description)
                    loop.call_soon_threadsafe(future.set_result, result)

                elif op == "commit":
                    self._conn.commit()
                    loop.call_soon_threadsafe(future.set_result, None)

                elif op == "rollback":
                    self._conn.rollback()
                    loop.call_soon_threadsafe(future.set_result, None)

                elif op == "close":
                    self._conn.close()
                    self._conn = None
                    loop.call_soon_threadsafe(future.set_result, None)
                    self._running = False
                    self._queue.task_done()
                    break

            except Exception as e:  # noqa: BLE001
                loop.call_soon_threadsafe(future.set_exception, e)
            finally:
                self._queue.task_done()

    def _drain_queue_with_error(self, error: Exception) -> None:
        """Cancel all queued items with the given exception."""
        while True:
            try:
                task = self._queue.get_nowait()
                if task[0] == "shutdown":
                    future, loop = task[1], task[2]
                    loop.call_soon_threadsafe(future.set_result, None)
                else:
                    op, *args, future, loop = task
                    loop.call_soon_threadsafe(future.set_exception, error)
                self._queue.task_done()
            except queue.Empty:
                break

    async def _ensure_initialized(self) -> None:
        """Ensure the background worker connection is ready."""
        if not self._init_event.is_set():
            await asyncio.to_thread(self._init_event.wait)
        if self._init_error:
            raise self._init_error

    # 5. Provide methods: execute(), execute_many(), commit(), rollback(), close()

    async def execute(
        self, sql: str, parameters: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> SovereignCursor:
        """Execute a query in the background thread."""
        if not self._running:
            raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
        await self._ensure_initialized()

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._queue.put(("execute", sql, parameters, future, loop))
        return await future

    async def execute_many(self, sql: str, seq_of_parameters: Sequence[Any]) -> SovereignCursor:
        """Execute a batch query in the background thread."""
        if not self._running:
            raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
        await self._ensure_initialized()

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._queue.put(("execute_many", sql, seq_of_parameters, future, loop))
        return await future

    async def commit(self) -> None:
        """Commit the current transaction in the background thread."""
        if not self._running:
            raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
        await self._ensure_initialized()

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._queue.put(("commit", future, loop))
        await future

    async def rollback(self) -> None:
        """Roll back the current transaction in the background thread."""
        if not self._running:
            raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
        await self._ensure_initialized()

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._queue.put(("rollback", future, loop))
        await future

    async def close(self) -> None:
        """Close the database connection and shut down the background thread."""
        if not self._running:
            return
        self._running = False

        # Don't wait for init if it failed, but wait if it's still initializing
        if not self._init_event.is_set():
            await asyncio.to_thread(self._init_event.wait)

        if self._init_error:
            # Thread already exited or failed
            return

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._queue.put(("shutdown", future, loop))
        await future

        # Safely join the background thread without blocking the event loop
        await asyncio.to_thread(self._thread.join, timeout=2.0)

    async def __aenter__(self) -> SovereignDB:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
