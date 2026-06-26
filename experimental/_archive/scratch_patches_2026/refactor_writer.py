import re

with open("cortex/database/writer.py") as f:
    code = f.read()

# Imports
if "import queue" not in code:
    code = code.replace("import asyncio\n", "import asyncio\nimport queue\nimport threading\n")

# __init__
code = code.replace("self._queue: asyncio.Queue[_Message] = asyncio.Queue(maxsize=queue_size)", "self._queue: queue.Queue[_Message] = queue.Queue(maxsize=queue_size)")
code = code.replace("self._task: asyncio.Task[None] | None = None", "self._thread: threading.Thread | None = None")

# start
code = re.sub(
    r"self\._conn = await self\._loop\.run_in_executor\(None, self\._create_connection\)\s+self\._task = asyncio\.create_task\(self\._writer_loop\(\), name=.cortex-sqlite-writer.\)",
    r"self._thread = threading.Thread(target=self._writer_loop, args=(self._loop,), name='cortex-sqlite-writer', daemon=True)\n        self._thread.start()",
    code
)

# is_running
code = code.replace("return self._started and self._task is not None and not self._task.done()", "return self._started and self._thread is not None and self._thread.is_alive()")

# enqueueing methods
code = re.sub(r"await self\._queue\.put\((.*?)\)", r"await loop.run_in_executor(None, self._queue.put, \1)", code)

# stop wait
code = code.replace("""            if self._task:
                self._task.cancel()""", """            pass""")

# _writer_loop definition
code = code.replace("async def _writer_loop(self) -> None:", "def _writer_loop(self, loop: asyncio.AbstractEventLoop) -> None:")
code = code.replace("loop = asyncio.get_running_loop()", "")
code = code.replace("assert self._conn is not None\n        conn = self._conn", "conn = self._create_connection()\n        self._conn = conn")

# inside _writer_loop: msg = await self._queue.get() -> msg = self._queue.get()
code = code.replace("msg = await self._queue.get()", "msg = self._queue.get()")
code = code.replace("should_exit = await self._dispatch_message(msg, conn, loop)", "should_exit = self._dispatch_message(msg, conn, loop)")

# _dispatch_message async -> def
code = code.replace("async def _dispatch_message(", "def _dispatch_message(")
code = code.replace("await self._handle_shutdown", "self._handle_shutdown")
code = code.replace("await self._process_write", "self._process_write")
code = code.replace("await self._handle_tx_sql", "self._handle_tx_sql")

# _handle_shutdown
code = code.replace("async def _handle_shutdown(", "def _handle_shutdown(")
code = code.replace("while not self._queue.empty():", "while not self._queue.empty():")
code = code.replace("remaining = self._queue.get_nowait()", "remaining = self._queue.get_nowait()")

# _handle_tx_sql
code = code.replace("async def _handle_tx_sql(", "def _handle_tx_sql(")
code = code.replace("await loop.run_in_executor(None, conn.execute, sql)", "conn.execute(sql)")

# _process_write
code = code.replace("async def _process_write(", "def _process_write(")
code = code.replace("cursor = await loop.run_in_executor(None, lambda: conn.execute(op.sql, op.params))", "cursor = conn.execute(op.sql, op.params)")
code = code.replace("await loop.run_in_executor(None, conn.commit)", "conn.commit()")
code = code.replace("await self._maybe_checkpoint(conn, loop)", "self._maybe_checkpoint(conn, loop)")

# _maybe_checkpoint
code = code.replace("async def _maybe_checkpoint(", "def _maybe_checkpoint(")
code = code.replace("await loop.run_in_executor(None, lambda: conn.execute(\"PRAGMA wal_checkpoint(PASSIVE)\"))", "conn.execute(\"PRAGMA wal_checkpoint(PASSIVE)\")")

with open("cortex/database/writer.py", "w") as f:
    f.write(code)
print("writer.py refactored")
