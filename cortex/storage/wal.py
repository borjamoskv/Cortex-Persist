import asyncio
import json
import logging
import time

from cortex.database.core import connect_async

logger = logging.getLogger(__name__)

WAL_PATH = "cortex/data/batch_wal.db"
BATCH_WINDOW_MS = 50


class WriteAheadLog:
    """
    Asynchronous Write-Ahead Log with Background Batching.
    Every async event is materialized in the WAL (status='pending')
    BEFORE entering the in-memory batch queue.

    On crash recovery, unsealed events are replayed.
    """

    def __init__(self, db_path: str = WAL_PATH):
        self.db_path = db_path
        self._conn = None
        self._queue = None
        self._worker_task = None

    async def connect(self):
        if self._conn is None:
            self._conn = await connect_async(self.db_path)
            await self._init_db()
            self._queue = asyncio.Queue()
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def close(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _init_db(self):
        assert self._conn is not None
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS batch_wal (
                event_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                received_at_epoch_ms INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'sealed', 'rejected')),
                event_hash TEXT,
                previous_hash TEXT
            )
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wal_status
            ON batch_wal(status)
        """)
        await self._conn.commit()

    async def _worker_loop(self):
        assert self._conn is not None
        while True:
            try:
                batch = []
                task = await self._queue.get()
                batch.append(task)
                
                # Wait for batch window to collect more tasks
                await asyncio.sleep(BATCH_WINDOW_MS / 1000.0)
                while not self._queue.empty():
                    batch.append(self._queue.get_nowait())
                
                inserts = [t[1] for t in batch if t[0] == "insert"]
                seals = [t[1] for t in batch if t[0] == "seal"]
                rejects = [t[1] for t in batch if t[0] == "reject"]
                
                if inserts:
                    await self._conn.executemany(
                        "INSERT OR IGNORE INTO batch_wal (event_id, payload, received_at_epoch_ms, status, event_hash, previous_hash) VALUES (?, ?, ?, 'pending', ?, ?)",
                        inserts
                    )
                if seals:
                    seal_ids = [eid for sublist in seals for eid in sublist]
                    if seal_ids:
                        placeholders = ','.join('?' * len(seal_ids))
                        await self._conn.execute(f"UPDATE batch_wal SET status = 'sealed' WHERE event_id IN ({placeholders})", seal_ids)
                if rejects:
                    reject_ids = [eid for sublist in rejects for eid in sublist]
                    if reject_ids:
                        placeholders = ','.join('?' * len(reject_ids))
                        await self._conn.execute(f"UPDATE batch_wal SET status = 'rejected' WHERE event_id IN ({placeholders})", reject_ids)
                        
                await self._conn.commit()
                
                for t in batch:
                    if not t[2].done():
                        t[2].set_result(True)
                    self._queue.task_done()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WAL] Batch worker failed: {e}")
                for t in batch:
                    if not t[2].done():
                        t[2].set_exception(e)
                    self._queue.task_done()

    async def write_pending(self, event_id: str, payload: dict, previous_hash: str | None = None) -> str:
        """Atomic write before memory queue insertion. Returns the event_hash."""
        if self._conn is None:
            await self.connect()
            
        import hashlib
        payload_str = json.dumps(payload)
        now_ms = int(time.time() * 1000)
        
        # Calculate event hash for Rust validation
        hash_input = f"{event_id}:{payload_str}:{now_ms}:{previous_hash or 'genesis'}"
        event_hash = hashlib.sha3_256(hash_input.encode()).hexdigest()
        
        future = asyncio.get_running_loop().create_future()
        await self._queue.put(("insert", (event_id, payload_str, now_ms, event_hash, previous_hash), future))
        await future
        
        return event_hash

    async def seal_batch(self, event_ids: list[str]) -> None:
        """Mark as sealed after Merkle root is computed."""
        if not event_ids:
            return
        if self._conn is None:
            await self.connect()
            
        future = asyncio.get_running_loop().create_future()
        await self._queue.put(("seal", event_ids, future))
        await future

    async def recover_unsealed(self) -> list[dict]:
        """
        Called during bootstrap watchdog.
        Returns all pending events that were never sealed.
        """
        if self._conn is None:
            await self.connect()
        assert self._conn is not None
            
        cursor = await self._conn.execute(
            "SELECT payload FROM batch_wal WHERE status = 'pending'"
        )
        rows = [json.loads(row[0]) for row in await cursor.fetchall()]
        return rows

    async def mark_rejected(self, event_ids: list[str]) -> None:
        """Events that failed ZK validation or consensus."""
        if not event_ids:
            return
        if self._conn is None:
            await self.connect()
            
        future = asyncio.get_running_loop().create_future()
        await self._queue.put(("reject", event_ids, future))
        await future
