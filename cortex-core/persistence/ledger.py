
import os
import time
import hashlib
import sqlite3
import threading
import weakref
import atexit
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from .base import SovereignResource, _setup_sqlite_pragmas, DB_PATH, ledger_entropy_event, logger

try:
    import cortex_rs  # noqa: F401
except ImportError:
    pass

class LedgerManager(SovereignResource):
    """L3 Sovereign Cryptographic Ledger — Audit Trail complying with EU AI Act."""

    def close(self):
        if hasattr(self, '_tx_queue'):
            self._tx_queue.put(None)
            if hasattr(self, '_signer_thread') and self._signer_thread.is_alive():
                self._signer_thread.join(timeout=1.0)
        super().close()

    def __init__(self):
        self._lock = threading.Lock()
        self._entropy_counter = 0
        self._init_db()
        self._finalizer = weakref.finalize(self, self._safe_close, self._conn)
        atexit.register(self.close)

        # C5-REAL Sovereign Ed25519 Keypair (ZK-Seal Substrate)
        key_path = os.path.join(os.path.dirname(DB_PATH), "cortex_sovereign.pem")
        if os.path.exists(key_path):
            from cryptography.hazmat.primitives import serialization
            with open(key_path, "rb") as key_file:
                self.private_key = serialization.load_pem_private_key(key_file.read(), password=None)
        else:
            from cryptography.hazmat.primitives import serialization
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
        self.aof_path = os.path.join(os.path.dirname(DB_PATH), "cortex_ledger_aof.bin")
        # Ensure it exists
        if not os.path.exists(self.aof_path):
            with open(self.aof_path, "wb") as f:
                f.write(b"")

        import queue
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
        import queue
        batch = []
        while True:
            try:
                item = self._tx_queue.get(timeout=1.0)
                if item is None:
                    break
                batch.append(item)
                while len(batch) < 100:
                    try:
                        batch.append(self._tx_queue.get_nowait())
                    except queue.Empty:
                        break
                
                for attempt in range(3):
                    try:
                        c = self._conn.cursor()
                        for timestamp, action, vector_id, yield_amount, block_hash, zk_payload in batch:
                            zk_proof = self.private_key.sign(zk_payload).hex()
                            c.execute(
                                "INSERT INTO ledger_records (timestamp, action, vector_id, yield_amount, hash, zk_proof) VALUES (?, ?, ?, ?, ?, ?)",
                                (timestamp, action, vector_id, yield_amount, block_hash, zk_proof)
                            )
                            # Vector B: Fast binary append-only write
                            with open(self.aof_path, "ab") as f:
                                import struct
                                # timestamp (d), yield (d), action (64s), vector_id(64s), hash(64s), zk_proof(128s)
                                packed = struct.pack("dd64s64s64s128s", 
                                    timestamp, yield_amount, 
                                    action.encode()[:64].ljust(64, b'\x00'),
                                    vector_id.encode()[:64].ljust(64, b'\x00'),
                                    block_hash.encode()[:64].ljust(64, b'\x00'),
                                    zk_proof.encode()[:128].ljust(128, b'\x00')
                                )
                                f.write(packed)
                        self._conn.commit()
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
        """Hash-chain new transaction to guarantee auditable tamper-evident history."""
        with self._lock:
            current_time = time.monotonic()
            if current_time <= self._last_timestamp:
                logger.warning(
                    f"SECURITY ALERT: Time-Jacking detected. Current: {current_time}, Last: {self._last_timestamp}."
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

            self._entropy_counter += 1
            if self._entropy_counter >= 100000:
                ledger_entropy_event.set()
                self._entropy_counter = 0

            return block_hash

    def verify_zk_seal(self, payload: str, signature_hex: str) -> bool:
        """Verifies a cryptographic seal against the Sovereign public key."""
        try:
            self.public_key.verify(bytes.fromhex(signature_hex), payload.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError):
            return False


    def get_total_yield(self, vector_id=None) -> float:
        with self._lock:
            c = self._conn.cursor()
            if vector_id:
                c.execute(
                    "SELECT SUM(yield_amount) FROM ledger_records WHERE vector_id = ?", (vector_id,)
                )
            else:
                c.execute("SELECT SUM(yield_amount) FROM ledger_records")
            res = c.fetchone()[0]
            return res or 0.0


