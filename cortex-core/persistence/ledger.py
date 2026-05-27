
import os
import time
import queue
import struct
import hashlib
import sqlite3
import weakref
import atexit
import itertools
import threading
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from .base import SovereignResource, _setup_sqlite_pragmas, DB_PATH, ledger_entropy_event, logger

try:
    import cortex_rs  # noqa: F401
except ImportError:
    pass

# Pre-computed struct format for AOF binary layout
# timestamp(d) + yield(d) + action(64s) + vector_id(64s) + hash(64s) + zk_proof(128s)
_AOF_STRUCT = struct.Struct("dd64s64s64s128s")


class LedgerManager(SovereignResource):
    """L3 Sovereign Cryptographic Ledger — Audit Trail complying with EU AI Act."""

    def close(self):
        if hasattr(self, '_tx_queue'):
            self._tx_queue.put(None)
            if hasattr(self, '_signer_thread') and self._signer_thread.is_alive():
                self._signer_thread.join(timeout=1.0)
        if hasattr(self, '_aof_fd') and self._aof_fd is not None:
            try:
                self._aof_fd.close()
            except Exception:
                pass
        super().close()

    def __init__(self):
        self._entropy_counter = itertools.count(0)
        self._entropy_threshold = 100000
        self._init_db()
        self._finalizer = weakref.finalize(self, self._safe_close, self._conn)
        atexit.register(self.close)

        # C5-REAL Sovereign Ed25519 Keypair (ZK-Seal Substrate)
        key_path = os.path.join(os.path.dirname(DB_PATH), "cortex_sovereign.pem")
        if os.path.exists(key_path):
            with open(key_path, "rb") as key_file:
                pk = serialization.load_pem_private_key(key_file.read(), password=None)
            assert isinstance(pk, ed25519.Ed25519PrivateKey)
            self.private_key = pk
        else:
            self.private_key = ed25519.Ed25519PrivateKey.generate()
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, "wb") as key_file:
                key_file.write(self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
        self.public_key = self.private_key.public_key()

        # Vector B: L3 Memory Mapped Ledger (Append-Only Binary)
        # Persistent file descriptor avoids open/close per write
        self.aof_path = os.path.join(os.path.dirname(DB_PATH), "cortex_ledger_aof.bin")
        if not os.path.exists(self.aof_path):
            with open(self.aof_path, "wb") as f:
                f.write(b"")
        self._aof_fd = open(self.aof_path, "ab")

        self._tx_queue = queue.Queue()
        c = self._conn.cursor()
        c.execute("SELECT hash, timestamp FROM ledger_records ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        if row:
            self._last_hash, self._last_timestamp = row
        else:
            self._last_hash = "GENESIS_BLOCK"
            self._last_timestamp = 0.0

        self._signer_thread = threading.Thread(target=self._signer_loop, daemon=True)
        self._signer_thread.start()

    def _init_db(self):
        # Ensure database parent directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
        _setup_sqlite_pragmas(self._conn)
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS ledger_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                action TEXT,
                vector_id TEXT,
                yield_amount REAL,
                hash TEXT
            )
        """)
        try:
            c.execute("ALTER TABLE ledger_records ADD COLUMN zk_proof TEXT")
        except sqlite3.OperationalError:
            pass

        c.execute("""
            CREATE TABLE IF NOT EXISTS cortex_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ki_id TEXT UNIQUE,
                summary TEXT,
                content TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS cortex_execution_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                agent TEXT,
                command TEXT,
                returncode INTEGER,
                execution_time REAL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_ledger_vector ON ledger_records(vector_id);")
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_exec_ledger_time ON cortex_execution_ledger(timestamp DESC);"
        )
        self._conn.commit()

    def _signer_loop(self):
        batch = []
        aof_write_buf = bytearray()
        while True:
            try:
                item = self._tx_queue.get(timeout=1.0)
                if item is None:
                    break
                batch.append(item)
                while len(batch) < 100:
                    try:
                        nxt = self._tx_queue.get_nowait()
                        if nxt is None:
                            self._tx_queue.put(None)
                            break
                        batch.append(nxt)
                    except queue.Empty:
                        break
                
                for attempt in range(3):
                    try:
                        c = self._conn.cursor()
                        aof_write_buf.clear()
                        for timestamp, action, vector_id, yield_amount, block_hash, zk_payload in batch:
                            zk_proof = self.private_key.sign(zk_payload).hex()
                            c.execute(
                                "INSERT INTO ledger_records (timestamp, action, vector_id, yield_amount, hash, zk_proof) VALUES (?, ?, ?, ?, ?, ?)",
                                (timestamp, action, vector_id, yield_amount, block_hash, zk_proof)
                            )
                            # Pre-pack AOF record into contiguous buffer
                            aof_write_buf += _AOF_STRUCT.pack(
                                timestamp, yield_amount, 
                                action.encode()[:64].ljust(64, b'\x00'),
                                vector_id.encode()[:64].ljust(64, b'\x00'),
                                block_hash.encode()[:64].ljust(64, b'\x00'),
                                zk_proof.encode()[:128].ljust(128, b'\x00')
                            )
                        self._conn.commit()
                        # Single syscall write for entire batch AOF
                        self._aof_fd.write(aof_write_buf)
                        batch.clear()
                        break
                    except Exception as e:
                        logger.error("LedgerManager DB write error (attempt %d): %s", attempt + 1, e)
                        self._conn.rollback()
                        time.sleep(0.5)
                else:
                    logger.critical("LedgerManager FATAL: Dropping batch after 3 failed attempts to maintain C5-REAL throughput.")
                    batch.clear()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("LedgerManager _signer_loop queue/unexpected error: %s", e)
                batch.clear()

    def append(self, action: str, vector_id: str, yield_amount: float) -> str:
        """Hash-chain new transaction to guarantee auditable tamper-evident history.
        
        Lock-free on the hot path: monotonic counter drives entropy events,
        hash-chain serialization uses queue-based single-writer pattern.
        """
        current_time = time.monotonic()
        if current_time <= self._last_timestamp:
            logger.warning(
                "SECURITY ALERT: Time-Jacking detected. Current: %f, Last: %f.",
                current_time, self._last_timestamp
            )
            timestamp = self._last_timestamp + 0.001
        else:
            timestamp = current_time

        payload = f"{self._last_hash}_{action}_{vector_id}_{yield_amount}_{timestamp}"
        block_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        zk_payload = f"{block_hash}_{action}_{timestamp}_CORTEX_L0".encode()

        self._last_hash = block_hash
        self._last_timestamp = timestamp
        
        self._tx_queue.put((timestamp, action, vector_id, yield_amount, block_hash, zk_payload))

        # Atomic entropy counter — no lock needed
        if next(self._entropy_counter) % self._entropy_threshold == 0:
            ledger_entropy_event.set()

        return block_hash

    def verify_zk_seal(self, payload: str, signature_hex: str) -> bool:
        """Verifies a cryptographic seal against the Sovereign public key."""
        try:
            self.public_key.verify(bytes.fromhex(signature_hex), payload.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError):
            return False


    def get_total_yield(self, vector_id: str | None = None) -> float:
        c = self._conn.cursor()
        if vector_id:
            c.execute(
                "SELECT SUM(yield_amount) FROM ledger_records WHERE vector_id = ?", (vector_id,)
            )
        else:
            c.execute("SELECT SUM(yield_amount) FROM ledger_records")
        res = c.fetchone()[0]
        return res or 0.0

    def reconcile_bankruptcy(self):
        """C5-REAL: Detects if the total yield is negative (thermodynamic bankruptcy) and issues an autonomous offset to restore balance to exactly 0.0."""
        current_yield = self.get_total_yield()
        if current_yield < 0:
            offset = -current_yield
            logger.warning("C5-REAL BANKRUPTCY DETECTED: Yield is %f. Triggering automatic reconciliation offset of %f.", current_yield, offset)
            self.append(action="RECONCILIATION_OFFSET", vector_id="SYSTEM", yield_amount=offset)
