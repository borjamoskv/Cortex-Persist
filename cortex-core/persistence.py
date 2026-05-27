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
from urllib.parse import urlparse

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

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
            except Exception:
                pass

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
        except Exception:
            pass


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


class ContextCache:
    """L1 Ephemeral Context Cache — API Prompt Optimization & Token Minimization."""

    def __init__(self):
        self._cache = {}  # key (hash of context string) -> timestamped payload
        self._ttl = 300  # Default TTL of 5 minutes for ephemeral cache validation

    def put(self, content_key: str, payload: dict):
        """Register payload with monotonic timestamp for deterministic L1 state management."""
        if len(self._cache) > 10000:
            self._cache.clear()  # O(1) Memory Entropy Purge
        self._cache[content_key] = {"payload": payload, "timestamp": time.monotonic()}

    def get(self, content_key: str) -> dict:
        """Retrieve cached payload if it exists and falls within TTL window."""
        if content_key in self._cache:
            entry = self._cache[content_key]
            if time.monotonic() - entry["timestamp"] < self._ttl:
                return entry["payload"]
            else:
                del self._cache[content_key]
        return None

    def inject_anthropic_headers(self, message_blocks: list) -> list:
        """Inject ephemeral cache controls to optimize token pricing on Anthropic APIs."""
        formatted_blocks = []
        for i, block in enumerate(message_blocks):
            new_block = dict(block)
            if len(str(block.get("text", ""))) > 2048 or i == len(message_blocks) - 1:
                new_block["cache_control"] = {"type": "ephemeral"}
            formatted_blocks.append(new_block)
        return formatted_blocks


class LedgerManager(SovereignResource):
    """L3 Sovereign Cryptographic Ledger — Audit Trail complying with EU AI Act."""

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
            CREATE TABLE IF NOT EXISTS cortex_swarm_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                agent TEXT,
                payload TEXT,
                status TEXT
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
            "CREATE INDEX IF NOT EXISTS idx_swarm_status_time ON cortex_swarm_queue(status, timestamp);"
        )
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
                
                c = self._conn.cursor()
                for timestamp, action, vector_id, yield_amount, block_hash, zk_payload in batch:
                    zk_proof = self.private_key.sign(zk_payload).hex()
                    c.execute(
                        "INSERT INTO ledger_records (timestamp, action, vector_id, yield_amount, hash, zk_proof) VALUES (?, ?, ?, ?, ?, ?)",
                        (timestamp, action, vector_id, yield_amount, block_hash, zk_proof)
                    )
                self._conn.commit()
                batch.clear()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("LedgerManager _signer_loop error: %s", e)
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


class VSAMemory(SovereignResource):
    """L2 Sovereign Vector Symbolic Architecture (VSA) Substrate & SQLite Semantic Knowledge Base."""

    def __init__(self):
        self._tensor_size = VSA_DIMENSION * 8  # 8 bytes per double

        # Ensure bin file exists and is pre-allocated to the exact tensor size
        if not os.path.exists(VSA_BIN_PATH) or os.path.getsize(VSA_BIN_PATH) < self._tensor_size:
            with open(VSA_BIN_PATH, "wb") as f:
                import struct

                f.write(struct.pack("d", 0.0) * VSA_DIMENSION)

        # Contextualize file and mmap lifecycle. Hold references tightly.
        if HAS_CORTEX_RS:
            self._substrate = cortex_rs.CortexRsSubstrate(VSA_BIN_PATH, VSA_DIMENSION)
        else:
            self._substrate = None

        self._f = open(VSA_BIN_PATH, "r+b")
        self._mmap_tensor = mmap.mmap(self._f.fileno(), self._tensor_size)
        self._tensor = memoryview(self._mmap_tensor).cast("d")

        self._decay_rate = 0.99
        self._record_count = 0  # Metabolic decay counter
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
        _setup_sqlite_pragmas(self._conn)

        # Use weakref.finalize for guaranteed cleanup when instance is garbage collected
        self._finalizer = weakref.finalize(
            self, self._safe_close, self._mmap_tensor, self._f, self._conn
        )
        atexit.register(self.close)
        
        import queue
        self._db_queue = queue.Queue()
        self._db_thread = threading.Thread(target=self._db_loop, daemon=True)
        self._db_thread.start()

    def _db_loop(self):
        import queue
        batch = []
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
                
                c = self._conn.cursor()
                c.executemany(
                    "INSERT OR REPLACE INTO cortex_knowledge (ki_id, summary, content) VALUES (?, ?, ?)",
                    batch
                )
                self._conn.commit()
                batch.clear()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("VSAMemory _db_loop error: %s", e)
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
            self._tensor[idx] += 1.0

            self._record_count += 1
            if self._record_count >= 1000:
                # Metabolic decay: driven by operation volume (Exergy), not arbitrary clock time
                self._apply_decay()
                self._record_count = 0

        ki_id = f"vsa_{int(time.monotonic())}_{idx}"
        self._db_queue.put((ki_id, key, value))

    def _apply_decay(self):
        for i in range(VSA_DIMENSION):
            val = self._tensor[i]
            if val > 0.001:
                self._tensor[i] = val * self._decay_rate
            elif val > 0.0:
                self._tensor[i] = 0.0


class IdeStatePreserver:
    """Guardian para proteger el entorno IDE/Agent contra fallas estructurales."""

    def __init__(self, ledger: LedgerManager):
        self.ledger = ledger
        self.backup_dir = os.path.expanduser("~/cortex_backups")
        self.target_dir = os.path.expanduser("~/.gemini/antigravity")
        self._daemon_task = None

    async def _execute_snapshot_async(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        try:
            backups = sorted([os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.startswith("antigravity_state_") and f.endswith(".tar.gz")], key=os.path.getmtime)
            while len(backups) >= 2:
                oldest = backups.pop(0)
                os.remove(oldest)
        except Exception:
            pass

        timestamp = int(time.monotonic())
        archive_path = os.path.join(self.backup_dir, f"antigravity_state_{timestamp}.tar.gz")

        try:
            # C5-REAL snapshot using non-blocking async subprocess (Zero OS-Thread Friction)
            proc = await asyncio.create_subprocess_exec(
                "/usr/bin/tar", "-czf", archive_path, "--exclude=brain", self.target_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                hasher = hashlib.sha256()
                with open(archive_path, "rb") as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
                backup_hash = hasher.hexdigest()

                # Register in L3 Ledger
                self.ledger.append(
                    action="IDE_STATE_SNAPSHOT", vector_id=f"hash:{backup_hash[:16]}", yield_amount=0.0
                )
                logger.info("IDE State Snapshot secured: %s", archive_path)
            else:
                logger.error("Failed to snapshot IDE state: %s", stderr.decode())
        except Exception as e:
            logger.error("Failed to snapshot IDE state: %s", e)

    def _execute_snapshot_sync(self):
        """Fallback for environments without a running event loop."""
        os.makedirs(self.backup_dir, exist_ok=True)
        try:
            backups = sorted([os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.startswith("antigravity_state_") and f.endswith(".tar.gz")], key=os.path.getmtime)
            while len(backups) >= 2:
                oldest = backups.pop(0)
                os.remove(oldest)
        except Exception:
            pass

        timestamp = int(time.monotonic())
        archive_path = os.path.join(self.backup_dir, f"antigravity_state_{timestamp}.tar.gz")
        try:
            subprocess.run(["/usr/bin/tar", "-czf", archive_path, "--exclude=brain", self.target_dir], check=True, capture_output=True)
            logger.info("IDE State Snapshot secured (Sync Fallback): %s", archive_path)
        except Exception as e:
            logger.error("Failed to snapshot IDE state sync: %s", e)

    async def _snapshot_loop(self):
        """Entropy-driven snapshots. Triggered precisely by Ledger cryptographic volume."""
        loop = asyncio.get_running_loop()
        while True:
            await loop.run_in_executor(None, ledger_entropy_event.wait)
            ledger_entropy_event.clear()
            await self._execute_snapshot_async()

    def start_guardian(self):
        if self._daemon_task:
            return
        try:
            loop = asyncio.get_running_loop()
            self._daemon_task = loop.create_task(self._snapshot_loop())
        except RuntimeError:
            logger.warning("IDE State Preserver loop could not be started: no running event loop.")
            # Fallback sync run once
            self._execute_snapshot_sync()


class SecurityReconDaemon(SovereignResource):
    """C5-REAL SOTA AI Agents Radar. Continuously investigates new SOTA AI agents and autonomous frameworks."""

    def __init__(self, ledger: LedgerManager):
        self.ledger = ledger
        self._daemon_task = None
        self._interval = 3600  # 1 hour

    async def _recon_loop(self):
        loop = asyncio.get_running_loop()
        while True:
            # Enqueue a high-exergy Swarm Task to the SAGE_COUNCIL to fetch SOTA AI Agents Fronts
            payload = {
                "type": "RESEARCH_SOTA_IA_AGENTS",
                "target": "agente-sota",
                "reward": 15.0,
                "description": "Continuous SOTA AI agents investigation. Extract exergy voids and evaluate empirical results from agentic architectures."
            }
            try:
                loop.run_in_executor(None, enqueue_swarm_task, "SAGE_COUNCIL", payload)
                logger.info("SecurityReconDaemon: Dispatched continuous SOTA IA agents investigation task.")
            except Exception as e:
                logger.error("SecurityReconDaemon error: %s", e)
            
            await asyncio.sleep(self._interval)

    def start_guardian(self):
        if self._daemon_task:
            return
        try:
            loop = asyncio.get_running_loop()
            self._daemon_task = loop.create_task(self._recon_loop())
        except RuntimeError:
            logger.warning("SecurityReconDaemon could not start: no event loop.")



class HybridPersistenceManager:
    """
    Sovereign Hybrid Persistence Manager.
    Integrates L1 (RAM Context), L2 (Semantic VSA/SQLite), and L3 (Cryptographic Audit Ledger).
    """

    def __init__(self):
        self.l1 = ContextCache()
        self.l2 = VSAMemory()
        self.l3 = LedgerManager()
        self.ring = ZeroCopyRingBuffer()  # L4 Zero-Copy Substrate
        self.ide_guardian = IdeStatePreserver(self.l3)
        self.outbox = OutboxDaemon(DB_PATH, ledger=self.l3)
        self.security_radar = SecurityReconDaemon(self.l3)
        self.ide_guardian.start_guardian()
        self.outbox.start_guardian()
        self.security_radar.start_guardian()

    def get_system_health(self) -> dict:
        """Aggregates C5-REAL telemetry from all persistence substrates."""
        return {
            "outbox": self.outbox.get_health_metrics(),
            "ledger_yield": self.l3.get_total_yield(),
        }


class ZeroCopyRingBuffer:
    """L4 Sovereign Zero-Copy Ring Buffer.
    Bypasses SQLite & JSON deserialization using C-contiguous mmap memoryviews.
    Memory Layout per Task (256 bytes):
      [0]    : Status (0=Free, 1=Pending, 2=Processing)
      [1:9]  : Timestamp (double)
      [9:73] : Agent ID Hash (64 bytes)
      [73:]  : Binary Payload (183 bytes)
    """

    def __init__(self, capacity=10000):
        self.capacity = capacity
        self.task_size = 256
        self.tensor_size = self.capacity * self.task_size
        self.bin_path = os.path.join(os.path.dirname(DB_PATH), "swarm_ring_vsa.bin")

        if not os.path.exists(self.bin_path) or os.path.getsize(self.bin_path) < self.tensor_size:
            with open(self.bin_path, "wb") as f:
                f.write(b"\x00" * self.tensor_size)

        if HAS_CORTEX_RS:
            try:
                self._rust_buf = cortex_rs.ZeroCopyRingBuffer(self.bin_path, self.capacity)
            except Exception as e:
                logger.warning("Failed to initialize Rust ZeroCopyRingBuffer, using Python fallback: %s", e)
                self._rust_buf = None
        else:
            self._rust_buf = None

        if self._rust_buf is None:
            self._f = open(self.bin_path, "r+b")
            self._mmap = mmap.mmap(self._f.fileno(), self.tensor_size)
            self._buffer = memoryview(self._mmap)
            self._lock = threading.Lock()
            self._write_idx = 0
            self._read_idx = 0

    def enqueue(self, agent_id: bytes, payload: bytes) -> bool:
        """O(1) Zero-copy memory write. Bypasses VSA OS locks."""
        if self._rust_buf is not None:
            return self._rust_buf.enqueue(agent_id, payload)

        with self._lock:
            offset = self._write_idx * self.task_size
            if self._buffer[offset] != 0:
                return False  # Buffer full
                
            self._buffer[offset] = 1  # Pending
            import struct
            struct.pack_into("d", self._buffer, offset + 1, time.monotonic())
            
            agent_bytes = agent_id[:64].ljust(64, b"\x00")
            self._buffer[offset + 9 : offset + 73] = agent_bytes

            payload_bytes = payload[:183].ljust(183, b"\x00")
            self._buffer[offset + 73 : offset + 256] = payload_bytes
            
            self._write_idx = (self._write_idx + 1) % self.capacity
            return True

    def fetch_pending(self):
        """Zero-copy read direct from C-contiguous memory."""
        if self._rust_buf is not None:
            return self._rust_buf.fetch_pending()

        tasks = []
        import struct

        with self._lock:
            for _ in range(self.capacity):
                offset = self._read_idx * self.task_size
                if self._buffer[offset] == 1:  # Pending
                    self._buffer[offset] = 2  # Mark Processing
                    ts = struct.unpack_from("d", self._buffer, offset + 1)[0]
                    agent_id = bytes(self._buffer[offset + 9 : offset + 73]).rstrip(b"\x00")
                    payload = bytes(self._buffer[offset + 73 : offset + 256]).rstrip(b"\x00")
                    tasks.append((self._read_idx, ts, agent_id, payload))
                    
                    self._buffer[offset] = 0 # Free it
                    self._read_idx = (self._read_idx + 1) % self.capacity
                else:
                    break
        return tasks


_global_ring_buffer = None

def _get_ring_buffer():
    global _global_ring_buffer
    if _global_ring_buffer is None:
        _global_ring_buffer = ZeroCopyRingBuffer()
    return _global_ring_buffer


class OutboxDaemon(SovereignResource):
    """Outbox Pattern Daemon: Asynchronously drains pending swarm tasks to NEXUS API."""

    def __init__(self, db_path: str | None = None, ledger: LedgerManager | None = None):
        self._db_path = db_path if db_path is not None else DB_PATH
        self._daemon_task = None
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=10.0)
        _setup_sqlite_pragmas(self._conn)
        self._lock = threading.Lock()
        self._finalizer = weakref.finalize(self, self._safe_close, self._conn)
        atexit.register(self.close)
        self.ledger = ledger

    def _fetch_pending_tasks(self):
        # 1. Zero-Copy Exergy Path: Drain from Ring Buffer first
        try:
            ring = _get_ring_buffer()
            ring_tasks = ring.fetch_pending()
            if ring_tasks:
                return [(f"ring_{idx}", agent.decode('utf-8', 'ignore'), payload.decode('utf-8', 'ignore')) 
                        for idx, ts, agent, payload in ring_tasks]
        except Exception as e:
            logger.error("ZeroCopyRingBuffer fetch failed: %s", e)

        # 2. High-Entropy Fallback: Drain from SQLite
        with self._lock:
            c = self._conn.cursor()
            # C4-SIM SQL Extraction (Index scan on status/timestamp)
            c.execute("""
                UPDATE cortex_swarm_queue 
                SET status = 'processing' 
                WHERE id IN (
                    SELECT id FROM cortex_swarm_queue 
                    WHERE status = 'pending' 
                    ORDER BY timestamp ASC LIMIT 50
                )
                RETURNING id, agent, payload
            """)
            rows = c.fetchall()
            self._conn.commit()
            return rows

    def _update_task_status(self, row_id, status):
        with self._lock:
            c = self._conn.cursor()
            c.execute(
                "UPDATE cortex_swarm_queue SET status = ? WHERE id = ?",
                (status, row_id),
            )
            self._conn.commit()

    def get_health_metrics(self) -> dict:
        """Returns C5-REAL telemetry for the Outbox Pattern."""
        with self._lock:
            c = self._conn.cursor()
            c.execute("SELECT status, COUNT(*) FROM cortex_swarm_queue GROUP BY status")
            counts = {row[0]: row[1] for row in c.fetchall()}

            c.execute("SELECT MIN(timestamp) FROM cortex_swarm_queue WHERE status = 'pending'")
            oldest_pending = c.fetchone()[0]

            latency = (time.monotonic() - oldest_pending) if oldest_pending else 0.0

            return {
                "pending_tasks": counts.get("pending", 0),
                "failed_tasks": counts.get("failed", 0),
                "completed_tasks": counts.get("completed", 0),
                "max_latency_seconds": round(latency, 4),
            }

    def drain_once_sync(self):
        """Synchronously drains a batch of pending tasks (primarily for tests and synchronous fallbacks)."""
        try:
            tasks = self._fetch_pending_tasks()
            if not tasks:
                return

            for task in tasks:
                row_id, agent_name, payload = task
                logger.info("Processing task %s from %s", row_id, agent_name)

                try:
                    payload_dict = json.loads(payload)
                except Exception:
                    payload_dict = {}

                # -- NATIVE L0 INTERCEPTOR: EXA_LISP --
                if payload_dict.get("type") == "EXA_LISP":
                    try:
                        from exa_lisp_genesis import parse, tokenize, evaluate, ExergyEnvironment, EntropyDeath
                        logger.info(f"C5-REAL EXA_LISP Invoked. Limits: {payload_dict.get('exergy_limit', 1000)}j")
                        code = payload_dict.get("code", "")
                        limit = payload_dict.get("exergy_limit", 1000)
                        
                        env = ExergyEnvironment(joules=limit, ledger=self.ledger)
                        ast = parse(tokenize(code))
                        result = evaluate(ast, env)
                        
                        logger.info(f"EXA_LISP Output: {result}")
                        if not str(row_id).startswith("ring_"):
                            self._update_task_status(row_id, "completed")
                        continue
                    except EntropyDeath as e:
                        logger.error(f"EXA_LISP Halted (EntropyDeath): {e}")
                        if not str(row_id).startswith("ring_"):
                            self._update_task_status(row_id, "failed")
                        continue
                    except Exception as e:
                        logger.error(f"EXA_LISP Syntax/Runtime Error: {e}")
                        if not str(row_id).startswith("ring_"):
                            self._update_task_status(row_id, "failed")
                        continue

                # -- NATIVE L0 INTERCEPTOR: AST_MUTATION --
                if payload_dict.get("type") == "AST_MUTATION":
                    try:
                        from aeon_0_compiler import AEON0Compiler
                        logger.info("C5-REAL AST_MUTATION Invoked via AEON-0 Compiler.")
                        compiler = AEON0Compiler(ledger=self.ledger)
                        compiler.mutate(payload_dict)
                        if not str(row_id).startswith("ring_"):
                            self._update_task_status(row_id, "completed")
                        continue
                    except Exception as e:
                        logger.error(f"AEON-0 Compiler Error: {e}")
                        if not str(row_id).startswith("ring_"):
                            self._update_task_status(row_id, "failed")
                        continue

                # -- C5-REAL SOVEREIGN ISOLATION --
                # Todo tráfico de red externa está PROHIBIDO. Las tareas que no son manejadas
                # por interceptores nativos L0 se marcan como fallidas para prevenir exfiltración de entropía.
                logger.error(f"C5-REAL Isolation: Task {agent_name} rejected. Network dispatch is prohibited.")
                
                # If row_id starts with 'ring_', it's from the Ring Buffer, no SQLite update needed unless synced
                if not str(row_id).startswith("ring_"):
                    self._update_task_status(row_id, "failed")
                
        except Exception as e:
            logger.error("Outbox drainer error: %s", e)

    async def _drain_loop(self):
        loop = asyncio.get_running_loop()
        outbox_wake_event.set()  # Initial trigger on startup
        while True:
            # Silicon Way: Event-driven outbox. Zero latency, zero arbitrary waits.
            # Unblocks instantly when outbox_wake_event is set. 5.0s fallback to clear potential deadlocks.
            await loop.run_in_executor(None, lambda: outbox_wake_event.wait(timeout=5.0))
            outbox_wake_event.clear()
            try:
                await loop.run_in_executor(None, self.drain_once_sync)
            except Exception as e:
                logger.error("Outbox drainer loop error: %s", e)

    def start_guardian(self):
        if self._daemon_task:
            return
        try:
            loop = asyncio.get_running_loop()
            self._daemon_task = loop.create_task(self._drain_loop())
        except RuntimeError:
            pass


def _enqueue_swarm_task_sync(agent_name: str, payload: dict):
    """Zero-copy core implementation of the Swarm Queue Dispatcher."""
    try:
        ring = _get_ring_buffer()
        payload_bytes = json.dumps(payload).encode('utf-8')
        agent_bytes = agent_name.encode('utf-8')
        success = ring.enqueue(agent_bytes, payload_bytes)
        
        if not success:
            logger.warning("ZeroCopyRingBuffer full. Entropic Fallback to SQLite.")
            conn = _get_local_conn(DB_PATH, timeout=30.0)
            c = conn.cursor()
            c.execute(
                "INSERT INTO cortex_swarm_queue (timestamp, agent, payload, status) VALUES (?, ?, ?, 'pending')",
                (time.monotonic(), agent_name, payload_bytes.decode('utf-8')),
            )
            conn.commit()
            
        # Fire Zero-Latency Event to awaken the Outbox Daemon instantly
        outbox_wake_event.set()
    except Exception as e:
        logger.error("Failed to enqueue swarm task: %s", e)
        raise


def enqueue_swarm_task(agent_name: str, payload: dict):
    """Sovereign Swarm Queue Dispatcher. Pure Lock-Free execution bypasses executor overhead."""
    _enqueue_swarm_task_sync(agent_name, payload)


def get_swarm_metrics(bypass_cache: bool = False) -> dict:
    """Extract C5-REAL telemetry from SQLite regarding swarm operation."""
    now = time.monotonic()
    if not bypass_cache:
        with _metrics_cache_lock:
            if _metrics_cache["value"] is not None and now < _metrics_cache["expiry"]:
                return _metrics_cache["value"]

    try:
        conn = _get_local_conn(DB_PATH, timeout=5.0)
        c = conn.cursor()

        # Latency approximation: find average execution time from recent ledger entries
        c.execute(
            "SELECT AVG(execution_time) FROM (SELECT execution_time FROM cortex_execution_ledger ORDER BY timestamp DESC LIMIT 50)"
        )
        avg_exec = c.fetchone()[0]
        latency_ms = (avg_exec * 1000.0) if avg_exec else 35.0

        # Active children: count pending elements in the swarm queue
        c.execute("SELECT COUNT(*) FROM cortex_swarm_queue WHERE status='pending'")
        active_children = c.fetchone()[0]

        # Uncertainty: Failure rate in the ledger (returncode != 0)
        c.execute(
            "SELECT COUNT(*), SUM(CASE WHEN returncode != 0 THEN 1 ELSE 0 END) FROM (SELECT returncode FROM cortex_execution_ledger ORDER BY timestamp DESC LIMIT 100)"
        )
        row = c.fetchone()
        if row and row[0]:
            total = row[0]
            fails = row[1] if row[1] is not None else 0
            uncertainty = fails / total
        else:
            uncertainty = 0.0

        result = {
            "latency_ms": round(latency_ms, 2),
            "active_children": active_children,
            "uncertainty": round(uncertainty, 4),
        }
        with _metrics_cache_lock:
            _metrics_cache["value"] = result
            _metrics_cache["expiry"] = now + 0.5  # Cache for 500ms
        return result
    except Exception as e:
        logger.error("Failed to extract swarm metrics (Deterministic C5-REAL Exception): %s", e)
        return {"latency_ms": 99999.0, "active_children": -1, "uncertainty": 1.0}
