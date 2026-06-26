import re

with open("cortex/database/writer.py") as f:
    code = f.read()

# 1. Imports
code = code.replace("import asyncio\nimport logging\n", "import asyncio\nimport logging\nimport queue\nimport threading\n")

# 2. __init__
code = code.replace(
    "self._queue: asyncio.Queue[_Message] = asyncio.Queue(maxsize=queue_size)",
    "self._queue: queue.Queue[_Message] = queue.Queue(maxsize=queue_size)"
)
code = code.replace(
    "self._task: asyncio.Task[None] | None = None",
    "self._thread: threading.Thread | None = None"
)

# 3. is_running
code = code.replace(
    "return self._started and self._task is not None and not self._task.done()",
    "return self._started and self._thread is not None and self._thread.is_alive()"
)

# 4. start
start_target = """        # Create the connection in a thread to not block the event loop
        self._conn = await self._loop.run_in_executor(None, self._create_connection)

        self._task = asyncio.create_task(self._writer_loop(), name="cortex-sqlite-writer")"""
start_replacement = """        # Create the thread which will manage the connection
        self._thread = threading.Thread(target=self._writer_loop, args=(self._loop,), name="cortex-sqlite-writer", daemon=True)
        self._thread.start()"""
code = code.replace(start_target, start_replacement)

# 5. queue.put from async methods -> needs run_in_executor? No, queue.Queue.put_nowait is thread-safe.
# Actually queue.Queue.put is thread-safe, we can call it from asyncio directly without run_in_executor if we use put_nowait.
code = re.sub(r"await self\._queue\.put\((.*?)\)", r"self._queue.put(\1)", code)

# 6. stop
stop_target = """        # Wait for the writer to process remaining items and exit
        try:
            await asyncio.wait_for(shutdown.future, timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Writer shutdown timed out, cancelling task")
            if self._task:
                self._task.cancel()"""
stop_replacement = """        # Wait for the writer to process remaining items and exit
        try:
            await asyncio.wait_for(shutdown.future, timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Writer shutdown timed out, killing thread via daemon exit")"""
code = code.replace(stop_target, stop_replacement)

# 7. Internal Writer Loop
loop_target = """    async def _writer_loop(self) -> None:
        \"\"\"Main writer loop - processes messages sequentially.\"\"\"
        assert self._conn is not None
        conn = self._conn
        loop = asyncio.get_running_loop()"""
loop_replacement = """    def _writer_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        \"\"\"Main writer loop - processes messages sequentially.\"\"\"
        # Create connection in the dedicated thread
        self._conn = self._create_connection()
        conn = self._conn"""
code = code.replace(loop_target, loop_replacement)

code = code.replace("msg = await self._queue.get()", "msg = self._queue.get()")
code = code.replace("should_exit = await self._dispatch_message(msg, conn, loop)", "should_exit = self._dispatch_message(msg, conn, loop)")

# 8. _dispatch_message
disp_target = """    async def _dispatch_message(
        self,
        msg: _Message,
        conn: sqlite3.Connection,
        loop: asyncio.AbstractEventLoop,
    ) -> bool:
        \"\"\"Dispatch a single message. Returns True if loop should exit.\"\"\"
        if isinstance(msg, _Shutdown):
            await self._handle_shutdown(conn, loop, msg.future)
            return True
        if isinstance(msg, _WriteOp):
            await self._process_write(conn, msg, loop)
        elif isinstance(msg, _TxBegin):
            await self._handle_tx_sql(conn, loop, msg.future, "BEGIN IMMEDIATE")
        elif isinstance(msg, _TxCommit):
            await self._handle_tx_sql(conn, loop, msg.future, "COMMIT")
        elif isinstance(msg, _TxRollback):
            await self._handle_tx_sql(conn, loop, msg.future, "ROLLBACK")
        return False"""
disp_replacement = """    def _dispatch_message(
        self,
        msg: _Message,
        conn: sqlite3.Connection,
        loop: asyncio.AbstractEventLoop,
    ) -> bool:
        \"\"\"Dispatch a single message. Returns True if loop should exit.\"\"\"
        if isinstance(msg, _Shutdown):
            self._handle_shutdown(conn, loop, msg.future)
            return True
        if isinstance(msg, _WriteOp):
            self._process_write(conn, msg, loop)
        elif isinstance(msg, _TxBegin):
            self._handle_tx_sql(conn, loop, msg.future, "BEGIN IMMEDIATE")
        elif isinstance(msg, _TxCommit):
            self._handle_tx_sql(conn, loop, msg.future, "COMMIT")
        elif isinstance(msg, _TxRollback):
            self._handle_tx_sql(conn, loop, msg.future, "ROLLBACK")
        return False"""
code = code.replace(disp_target, disp_replacement)

# 9. _handle_shutdown
shut_target = """    async def _handle_shutdown(
        self,
        conn: sqlite3.Connection,
        loop: asyncio.AbstractEventLoop,
        fut: asyncio.Future,
    ) -> None:
        \"\"\"Drain remaining writes and signal shutdown complete.\"\"\"
        while not self._queue.empty():
            remaining = self._queue.get_nowait()
            if isinstance(remaining, _WriteOp):
                await self._process_write(conn, remaining, loop)
        loop.call_soon_threadsafe(fut.set_result, Ok(None))"""
shut_replacement = """    def _handle_shutdown(
        self,
        conn: sqlite3.Connection,
        loop: asyncio.AbstractEventLoop,
        fut: asyncio.Future,
    ) -> None:
        \"\"\"Drain remaining writes and signal shutdown complete.\"\"\"
        while not self._queue.empty():
            try:
                remaining = self._queue.get_nowait()
                if isinstance(remaining, _WriteOp):
                    self._process_write(conn, remaining, loop)
            except queue.Empty:
                break
        loop.call_soon_threadsafe(fut.set_result, Ok(None))"""
code = code.replace(shut_target, shut_replacement)

# 10. _handle_tx_sql
tx_target = """    async def _handle_tx_sql(
        self,
        conn: sqlite3.Connection,
        loop: asyncio.AbstractEventLoop,
        fut: asyncio.Future,
        sql: str,
    ) -> None:
        \"\"\"Execute a transaction control statement (BEGIN/COMMIT/ROLLBACK).\"\"\"
        try:
            await loop.run_in_executor(None, conn.execute, sql)
            loop.call_soon_threadsafe(fut.set_result, Ok(None))
        except sqlite3.Error as e:
            if sql == "ROLLBACK":
                logger.error("ROLLBACK failed: %s", e)
            loop.call_soon_threadsafe(fut.set_result, Err(f"{sql} failed: {e}"))"""
tx_replacement = """    def _handle_tx_sql(
        self,
        conn: sqlite3.Connection,
        loop: asyncio.AbstractEventLoop,
        fut: asyncio.Future,
        sql: str,
    ) -> None:
        \"\"\"Execute a transaction control statement (BEGIN/COMMIT/ROLLBACK).\"\"\"
        try:
            conn.execute(sql)
            loop.call_soon_threadsafe(fut.set_result, Ok(None))
        except sqlite3.Error as e:
            if sql == "ROLLBACK":
                logger.error("ROLLBACK failed: %s", e)
            loop.call_soon_threadsafe(fut.set_result, Err(f"{sql} failed: {e}"))"""
code = code.replace(tx_target, tx_replacement)

# 11. _process_write
proc_target = """    async def _process_write(
        self,
        conn: sqlite3.Connection,
        op: _WriteOp,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        \"\"\"Process a single write operation in the executor.\"\"\"
        start_wait = op.created_at if hasattr(op, "created_at") else time.monotonic()  # type: ignore[reportAttributeAccessIssue]
        wait_ms = (time.monotonic() - start_wait) * 1000
        try:
            start_exec = time.monotonic()
            cursor = await loop.run_in_executor(None, lambda: conn.execute(op.sql, op.params))
            # Auto-commit if not inside an explicit transaction
            if not conn.in_transaction:
                await loop.run_in_executor(None, conn.commit)
            exec_ms = (time.monotonic() - start_exec) * 1000

            # Update metrics
            ops = self._metrics["total_ops"]
            m_wait = self._metrics["avg_wait_ms"]
            m_exec = self._metrics["avg_exec_ms"]

            # Use weighted moving average to prevent overflow and keep metrics responsive
            self._metrics["avg_wait_ms"] = (m_wait * ops + wait_ms) / (ops + 1)
            self._metrics["avg_exec_ms"] = (m_exec * ops + exec_ms) / (ops + 1)
            self._metrics["total_ops"] += 1

            loop.call_soon_threadsafe(op.future.set_result, Ok(cursor.rowcount))

            # Periodic WAL checkpoint to prevent unbounded WAL growth
            self._write_count += 1
            if self._write_count >= self._CHECKPOINT_INTERVAL:
                await self._maybe_checkpoint(conn, loop)

        except sqlite3.Error as e:
            logger.warning("Write failed: %s | SQL: %s", e, op.sql[:100])
            loop.call_soon_threadsafe(
                op.future.set_result,
                Err(f"SQLite write error: {e}"),
            )"""
proc_replacement = """    def _process_write(
        self,
        conn: sqlite3.Connection,
        op: _WriteOp,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        \"\"\"Process a single write operation in the executor.\"\"\"
        start_wait = op.created_at if hasattr(op, "created_at") else time.monotonic()  # type: ignore[reportAttributeAccessIssue]
        wait_ms = (time.monotonic() - start_wait) * 1000
        try:
            start_exec = time.monotonic()
            cursor = conn.execute(op.sql, op.params)
            # Auto-commit if not inside an explicit transaction
            if not conn.in_transaction:
                conn.commit()
            exec_ms = (time.monotonic() - start_exec) * 1000

            # Update metrics
            ops = self._metrics["total_ops"]
            m_wait = self._metrics["avg_wait_ms"]
            m_exec = self._metrics["avg_exec_ms"]

            # Use weighted moving average to prevent overflow and keep metrics responsive
            self._metrics["avg_wait_ms"] = (m_wait * ops + wait_ms) / (ops + 1)
            self._metrics["avg_exec_ms"] = (m_exec * ops + exec_ms) / (ops + 1)
            self._metrics["total_ops"] += 1

            loop.call_soon_threadsafe(op.future.set_result, Ok(cursor.rowcount))

            # Periodic WAL checkpoint to prevent unbounded WAL growth
            self._write_count += 1
            if self._write_count >= self._CHECKPOINT_INTERVAL:
                self._maybe_checkpoint(conn, loop)

        except sqlite3.Error as e:
            logger.warning("Write failed: %s | SQL: %s", e, op.sql[:100])
            loop.call_soon_threadsafe(
                op.future.set_result,
                Err(f"SQLite write error: {e}"),
            )"""
code = code.replace(proc_target, proc_replacement)

# 12. _maybe_checkpoint
check_target = """    async def _maybe_checkpoint(
        self, conn: sqlite3.Connection, loop: asyncio.AbstractEventLoop
    ) -> None:
        \"\"\"Perform a WAL checkpoint if the interval has been reached.\"\"\"
        try:
            await loop.run_in_executor(None, lambda: conn.execute("PRAGMA wal_checkpoint(PASSIVE)"))
            self._write_count = 0
            logger.debug("Periodic WAL checkpoint at %d writes", self._CHECKPOINT_INTERVAL)
        except sqlite3.Error as e:
            logger.debug("WAL checkpoint deferred: %s", e)"""
check_replacement = """    def _maybe_checkpoint(
        self, conn: sqlite3.Connection, loop: asyncio.AbstractEventLoop
    ) -> None:
        \"\"\"Perform a WAL checkpoint if the interval has been reached.\"\"\"
        try:
            conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            self._write_count = 0
            logger.debug("Periodic WAL checkpoint at %d writes", self._CHECKPOINT_INTERVAL)
        except sqlite3.Error as e:
            logger.debug("WAL checkpoint deferred: %s", e)"""
code = code.replace(check_target, check_replacement)

with open("cortex/database/writer.py", "w") as f:
    f.write(code)
print("writer.py successfully refactored")
