
import os
import time
import queue
import struct
import hashlib
import sqlite3
import threading
import mmap
import weakref
import atexit

from .base import SovereignResource, _setup_sqlite_pragmas, DB_PATH, VSA_BIN_PATH, VSA_DIMENSION, HAS_CORTEX_RS, logger

try:
    import cortex_rs
except ImportError:
    pass

class VSAMemory(SovereignResource):
    """L2 Sovereign Vector Symbolic Architecture (VSA) Substrate & SQLite Semantic Knowledge Base."""

    def close(self):
        if hasattr(self, "_finalizer") and self._finalizer is not None and self._finalizer.alive:
            self._finalizer.detach()
        if hasattr(self, '_db_queue'):
            self._db_queue.put(None)
            if hasattr(self, '_db_thread') and self._db_thread.is_alive():
                self._db_thread.join(timeout=1.0)
        if hasattr(self, "_tensor") and self._tensor is not None:
            try:
                self._tensor.release()
            except ValueError:
                pass
            self._tensor = None
        if hasattr(self, "_base_view") and self._base_view is not None:
            try:
                self._base_view.release()
            except ValueError:
                pass
            self._base_view = None
        if hasattr(self, "_mmap_tensor") and self._mmap_tensor is not None:
            try:
                self._mmap_tensor.close()
            except ValueError:
                pass
            self._mmap_tensor = None
        if hasattr(self, "_f") and self._f is not None:
            try:
                self._f.close()
            except OSError:
                pass
            self._f = None
        super().close()

    def __init__(self):
        self._tensor_size = VSA_DIMENSION * 8  # 8 bytes per double

        # Ensure bin file exists and is pre-allocated to the exact tensor size
        if not os.path.exists(VSA_BIN_PATH) or os.path.getsize(VSA_BIN_PATH) < self._tensor_size:
            with open(VSA_BIN_PATH, "wb") as f:
                f.write(struct.pack("d", 0.0) * VSA_DIMENSION)

        # Contextualize file and mmap lifecycle. Hold references tightly.
        if HAS_CORTEX_RS:
            self._substrate = cortex_rs.CortexRsSubstrate(VSA_BIN_PATH, VSA_DIMENSION)
        else:
            self._substrate = None

        self._f = open(VSA_BIN_PATH, "r+b")
        self._mmap_tensor = mmap.mmap(self._f.fileno(), self._tensor_size)
        self._base_view = memoryview(self._mmap_tensor)
        self._tensor = self._base_view.cast("d")

        self._decay_rate = 0.99
        self._record_count = 0  # Metabolic decay counter
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
        _setup_sqlite_pragmas(self._conn)

        # FIX(P0): finalize AFTER all resources are assigned (not getattr which captured None)
        self._finalizer = weakref.finalize(
            self, self._safe_close, self._tensor, self._base_view, self._mmap_tensor, self._f, self._conn
        )
        atexit.register(self.close)
        
        self._db_queue: queue.Queue = queue.Queue()
        self._db_thread = threading.Thread(target=self._db_loop, daemon=True)
        self._db_thread.start()

    def _db_loop(self):
        batch: list = []
        while True:
            try:
                item = self._db_queue.get(timeout=1.0)
                if item is None:
                    break
                batch.append(item)
                while len(batch) < 100:
                    try:
                        batch.append(self._db_queue.get_nowait())
                    except queue.Empty:
                        break
                
                for attempt in range(3):
                    try:
                        c = self._conn.cursor()
                        c.executemany(
                            "INSERT OR REPLACE INTO cortex_knowledge (ki_id, summary, content) VALUES (?, ?, ?)",
                            batch
                        )
                        self._conn.commit()
                        batch.clear()
                        break
                    except Exception as e:
                        logger.error("VSAMemory DB write error (attempt %d): %s", attempt + 1, e)
                        self._conn.rollback()
                        time.sleep(0.5)
                else:
                    logger.critical("VSAMemory FATAL: Dropping batch after 3 failed attempts to maintain VSA throughput.")
                    batch.clear()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("VSAMemory _db_loop queue/unexpected error: %s", e)
                batch.clear()

    def record(self, key: str, value: str):
        """Map semantic trace to both RAM tensor and Persistent SQLite FTS5."""
        ctx_string = f"{key}:{value}"
        idx = int(hashlib.sha256(ctx_string.encode("utf-8")).hexdigest(), 16) % VSA_DIMENSION

        if self._substrate is not None:
            try:
                self._substrate.record(key, value)
                self._record_count += 1
                if self._record_count >= 1000:
                    self._substrate.apply_decay(self._decay_rate)
                    self._record_count = 0
            except Exception as e:
                logger.error("Rust VSA Record Failure: %s", e)
        else:
            # Zero-copy Silicon Direct Access
            self._tensor[idx] += 1.0  # pyright: ignore[reportOptionalSubscript]

            self._record_count += 1
            if self._record_count >= 1000:
                # Metabolic decay: driven by operation volume (Exergy), not arbitrary clock time
                self._apply_decay()
                self._record_count = 0

        ki_id = f"vsa_{int(time.monotonic())}_{idx}"
        self._db_queue.put((ki_id, key, value))

    def _apply_decay(self):
        for i in range(VSA_DIMENSION):
            val = self._tensor[i]  # pyright: ignore[reportOptionalSubscript]
            if val > 0.001:
                self._tensor[i] = val * self._decay_rate  # pyright: ignore[reportOptionalSubscript]
            elif val > 0.0:
                self._tensor[i] = 0.0  # pyright: ignore[reportOptionalSubscript]
