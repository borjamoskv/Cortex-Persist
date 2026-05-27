import os
import logging
import sqlite3
import threading
import atexit
import itertools

try:
    import cortex_rs  # noqa: F401
    HAS_CORTEX_RS = True
except ImportError:
    HAS_CORTEX_RS = False

logger = logging.getLogger("cortex.persistence")

# C5-REAL Asynchronous Silicon Events (Zero Biological Time)
outbox_wake_event = threading.Event()
ledger_entropy_event = threading.Event()

# Exergy-Maximized Thread-Local Connection Pool
_local = threading.local()

# Lock-Free Metrics Cache: Atomic epoch-based invalidation
# Writers increment _metrics_epoch; readers compare snapshot epoch to current.
# No Lock. No contention. O(1) deterministic.
_metrics_epoch = itertools.count(0)
_metrics_cache = {"value": None, "expiry": 0.0, "epoch": -1}
_metrics_cache_lock = threading.Lock()  # Retained for backward compat imports; unused in hot path

# Monotonic clock anchor for deterministic timing across all layers
_BOOT_MONOTONIC = __import__("time").monotonic()


def _setup_sqlite_pragmas(conn: sqlite3.Connection) -> None:
    """Apply C5-REAL performance pragmas to an SQLite connection."""
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-64000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA mmap_size=268435456;")  # 256MB mmap for zero-copy reads


class SovereignResource:
    """Base class for autonomous cleanup of file descriptors and connections via weakref."""
    _finalizer = None

    @staticmethod
    def _safe_close(*resources):
        for res in resources:
            try:
                if res:
                    if hasattr(res, 'release'):
                        try:
                            res.release()
                        except ValueError:
                            pass
                    elif hasattr(res, 'close'):
                        try:
                            res.close()
                        except ValueError:
                            pass
            except Exception as e:
                logger.warning("Silenced exception: %s", e)

    def close(self):
        if hasattr(self, "_finalizer") and self._finalizer is not None and self._finalizer.alive:
            self._finalizer()

    def __del__(self):
        self.close()


def _close_local_conn():
    """Cleanup thread-local connection on process exit."""
    conn = getattr(_local, "conn", None)
    if conn:
        try:
            conn.close()
        except Exception as e:
            logger.warning("Silenced exception: %s", e)


atexit.register(_close_local_conn)


def _get_local_conn(db_path: str, timeout: float = 30.0) -> sqlite3.Connection:
    """Thread-local SQLite connection pool with automatic pragma initialization."""
    if getattr(_local, "db_path", None) != db_path or not hasattr(_local, "conn"):
        _local.db_path = db_path
        _local.conn = sqlite3.connect(db_path, timeout=timeout)
        _setup_sqlite_pragmas(_local.conn)
    return _local.conn


VSA_DIMENSION = 10000
VSA_BIN_PATH = os.getenv("VSA_BIN_PATH", "/Users/borjafernandezangulo/10_PROJECTS/vsa_nexus.bin")
DB_PATH = os.getenv(
    "CORTEX_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cortex_memory_vsa.db"),
)

__all__ = [
    "SovereignResource",
    "_setup_sqlite_pragmas",
    "DB_PATH",
    "VSA_BIN_PATH",
    "VSA_DIMENSION",
    "HAS_CORTEX_RS",
    "outbox_wake_event",
    "ledger_entropy_event",
    "_get_local_conn",
    "logger",
    "_metrics_cache",
    "_metrics_cache_lock",
]
