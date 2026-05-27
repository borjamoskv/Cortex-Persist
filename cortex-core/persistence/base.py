import os
import json
import time
import hashlib
import asyncio
import logging
import sqlite3
import subprocess
import threading
import mmap
import weakref
import atexit
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from ultramap import UltramapSubstrate

try:
    import cortex_rs
    HAS_CORTEX_RS = True
except ImportError:
    HAS_CORTEX_RS = False

# C5-REAL Asynchronous Silicon Events (Zero Biological Time)
outbox_wake_event = threading.Event()
ledger_entropy_event = threading.Event()

# Exergy-Maximized Thread-Local Connection Pool
_local = threading.local()

# Metrics Cache to reduce database read contention in concurrent swarms
_metrics_cache = {"value": None, "expiry": 0.0}
_metrics_cache_lock = threading.Lock()



def _setup_sqlite_pragmas(conn):
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-64000;")
    conn.execute("PRAGMA temp_store=MEMORY;")


class SovereignResource:
    """Base class for autonomous cleanup of file descriptors and connections via weakref."""
    @staticmethod
    def _safe_close(*resources):
        for res in resources:
            try:
                if res:
                    res.close()
            except Exception as e:
                logger.warning(f'Silenced exception: {e}')

    def close(self):
        if hasattr(self, "_finalizer") and self._finalizer.alive:
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
            logger.warning(f'Silenced exception: {e}')


atexit.register(_close_local_conn)


def _get_local_conn(db_path, timeout=30.0):
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

logger = logging.getLogger("cortex.persistence")


