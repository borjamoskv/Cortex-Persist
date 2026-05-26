import os
import json
import time
import hashlib
import asyncio
import logging
import sqlite3
import fcntl
import subprocess
import threading
import mmap
import weakref
import atexit
import concurrent.futures
from urllib.parse import urlparse

# Exergy-Maximized Thread-Local Connection Pool
_local = threading.local()


def _get_local_conn(db_path, timeout=30.0):
    if getattr(_local, "db_path", None) != db_path or not hasattr(_local, "conn"):
        _local.db_path = db_path
        _local.conn = sqlite3.connect(db_path, timeout=timeout)
        _local.conn.execute("PRAGMA journal_mode=WAL;")
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
        """Register payload with local timestamp for L1 state management."""
        self._cache[content_key] = {"payload": payload, "timestamp": time.time()}

    def get(self, content_key: str) -> dict:
        """Retrieve cached payload if it exists and falls within TTL window."""
        if content_key in self._cache:
            entry = self._cache[content_key]
            if time.time() - entry["timestamp"] < self._ttl:
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


class LedgerManager:
    """L3 Sovereign Cryptographic Ledger — Audit Trail complying with EU AI Act."""

    def __init__(self):
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        # Ensure database parent directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
        c = self._conn.cursor()
        c.execute("PRAGMA journal_mode=WAL;")
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
        self._conn.commit()

    def append(self, action: str, vector_id: str, yield_amount: float) -> str:
        """Hash-chain new transaction to guarantee auditable tamper-evident history."""
        with self._lock:
            c = self._conn.cursor()
            # Get previous hash
            c.execute("SELECT hash FROM ledger_records ORDER BY id DESC LIMIT 1")
            row = c.fetchone()
            prev_hash = row[0] if row else "GENESIS_BLOCK"

            timestamp = time.time()
            payload = f"{prev_hash}_{action}_{vector_id}_{yield_amount}_{timestamp}"
            block_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

            c.execute(
                """
                INSERT INTO ledger_records (timestamp, action, vector_id, yield_amount, hash)
                VALUES (?, ?, ?, ?, ?)
            """,
                (timestamp, action, vector_id, yield_amount, block_hash),
            )
            self._conn.commit()
            return block_hash

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


class VSAMemory:
    """L2 Sovereign Vector Symbolic Architecture (VSA) Substrate & SQLite Semantic Knowledge Base."""

    def __init__(self):
        self._tensor_size = VSA_DIMENSION * 8  # 8 bytes per double

        # Ensure bin file exists and is pre-allocated to the exact tensor size
        if not os.path.exists(VSA_BIN_PATH) or os.path.getsize(VSA_BIN_PATH) < self._tensor_size:
            with open(VSA_BIN_PATH, "wb") as f:
                import struct

                f.write(struct.pack("d", 0.0) * VSA_DIMENSION)

        # Contextualize file and mmap lifecycle. Hold references tightly.
        self._f = open(VSA_BIN_PATH, "r+b")
        self._mmap_tensor = mmap.mmap(self._f.fileno(), self._tensor_size)
        self._tensor = memoryview(self._mmap_tensor).cast("d")

        self._decay_rate = 0.99
        self._daemon_task = None
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
        self._conn.execute("PRAGMA journal_mode=WAL;")

        # Use weakref.finalize for guaranteed cleanup when instance is garbage collected
        self._finalizer = weakref.finalize(
            self, self._cleanup, self._mmap_tensor, self._f, self._conn
        )
        atexit.register(self.close)

    @staticmethod
    def _cleanup(mmap_obj, file_obj, conn_obj):
        """Static cleanup method to avoid keeping references to self."""
        try:
            if mmap_obj:
                mmap_obj.close()
            if file_obj:
                file_obj.close()
            if conn_obj:
                conn_obj.close()
        except Exception:
            pass

    def close(self):
        """Explicitly invoke the finalizer to close descriptors."""
        if hasattr(self, "_finalizer") and self._finalizer.alive:
            self._finalizer()

    def __del__(self):
        self.close()

    def record(self, key: str, value: str):
        """Map semantic trace to both RAM tensor and Persistent SQLite FTS5."""
        ctx_string = f"{key}:{value}"
        idx = int(hashlib.sha256(ctx_string.encode("utf-8")).hexdigest(), 16) % VSA_DIMENSION

        # Zero-copy Silicon Direct Access
        self._tensor[idx] += 1.0

        try:
            with self._lock:
                c = self._conn.cursor()
                ki_id = f"vsa_{int(time.time())}_{idx}"
                c.execute(
                    "INSERT OR REPLACE INTO cortex_knowledge (ki_id, summary, content) VALUES (?, ?, ?)",
                    (ki_id, key, value),
                )
                self._conn.commit()
        except Exception as e:
            logger.error("VSA SQLite Record Failure: %s", e)

    async def _decay_loop(self):
        """Periodically decay high-dimensional state space to model biological memory loss."""
        while True:
            await asyncio.sleep(60)
            for i in range(VSA_DIMENSION):
                val = self._tensor[i]
                if val > 0.001:
                    self._tensor[i] = val * self._decay_rate
                elif val > 0.0:
                    self._tensor[i] = 0.0

    def start_glia(self):
        """Start the background neural decay process safely."""
        if self._daemon_task:
            return
        try:
            loop = asyncio.get_running_loop()
            self._daemon_task = loop.create_task(self._decay_loop())
        except RuntimeError:
            logger.warning("VSA neural decay loop could not be started: no running event loop.")


class IdeStatePreserver:
    """Guardian para proteger el entorno IDE/Agent contra fallas estructurales (Antigravity Drama)."""

    def __init__(self, ledger: LedgerManager):
        self.ledger = ledger
        self.backup_dir = os.path.expanduser("~/cortex_backups")
        self.target_dir = os.path.expanduser("~/.gemini/antigravity")
        self._daemon_task = None

    def _execute_snapshot(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        timestamp = int(time.time())
        archive_path = os.path.join(self.backup_dir, f"antigravity_state_{timestamp}.tar.gz")

        try:
            # C5-REAL snapshot using system tar
            subprocess.run(
                ["/usr/bin/tar", "-czf", archive_path, "--exclude=brain", self.target_dir],
                check=True,
                capture_output=True,
            )

            # Hash the backup
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
        except Exception as e:
            logger.error("Failed to snapshot IDE state: %s", e)

    async def _snapshot_loop(self):
        """Perform daily snapshots of IDE state to prevent entropy accumulation."""
        while True:
            self._execute_snapshot()
            await asyncio.sleep(86400)  # 24 hours

    def start_guardian(self):
        if self._daemon_task:
            return
        try:
            loop = asyncio.get_running_loop()
            self._daemon_task = loop.create_task(self._snapshot_loop())
        except RuntimeError:
            logger.warning("IDE State Preserver loop could not be started: no running event loop.")
            # Fallback sync run once
            self._execute_snapshot()


class HybridPersistenceManager:
    """
    Sovereign Hybrid Persistence Manager.
    Integrates L1 (RAM Context), L2 (Semantic VSA/SQLite), and L3 (Cryptographic Audit Ledger).
    """

    def __init__(self):
        self.l1 = ContextCache()
        self.l2 = VSAMemory()
        self.l3 = LedgerManager()
        self.ide_guardian = IdeStatePreserver(self.l3)
        self.outbox = OutboxDaemon(DB_PATH)
        self.l2.start_glia()
        self.ide_guardian.start_guardian()
        self.outbox.start_guardian()


class OutboxDaemon:
    """Outbox Pattern Daemon: Asynchronously drains pending swarm tasks to NEXUS API."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._daemon_task = None
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=10.0)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._lock = threading.Lock()

    def _fetch_pending_tasks(self):
        with self._lock:
            c = self._conn.cursor()
            c.execute(
                "SELECT id, agent, payload FROM cortex_swarm_queue WHERE status = 'pending' ORDER BY timestamp ASC LIMIT 50"
            )
            return c.fetchall()

    def _update_task_status(self, row_id, status):
        with self._lock:
            c = self._conn.cursor()
            c.execute(
                "UPDATE cortex_swarm_queue SET status = ? WHERE id = ?",
                (status, row_id),
            )
            self._conn.commit()

    async def _drain_loop(self):
        import urllib.request
        import urllib.error

        loop = asyncio.get_running_loop()
        while True:
            await asyncio.sleep(2)
            try:
                # C5-REAL: Offload SQLite I/O to prevent event loop blocking
                rows = await loop.run_in_executor(None, self._fetch_pending_tasks)
                if not rows:
                    continue

                nexus_url = os.getenv("NEXUS_API_URL", "http://localhost:8600")
                parsed_url = urlparse(nexus_url)
                if parsed_url.scheme not in ("https", "http") or (
                    parsed_url.scheme == "http"
                    and parsed_url.hostname not in ("localhost", "127.0.0.1")
                ):
                    logger.error("SECURITY ALERT: Invalid NEXUS_API_URL scheme/host.")
                    continue

                nexus_token = os.getenv("NEXUS_BEARER_TOKEN")
                if not nexus_token:
                    logger.error("SECURITY ALERT: NEXUS_BEARER_TOKEN missing.")
                    continue

                for row_id, agent_name, payload_str in rows:
                    try:
                        payload_dict = json.loads(payload_str)
                    except json.JSONDecodeError:
                        payload_dict = {}

                    caps_map = {
                        "VulnerabilityFixer": ["security", "code"],
                        "InvariantValidator": ["security", "code"],
                        "SAGE_COUNCIL": ["intel", "research"],
                        "OPTIMIZER": ["code"],
                    }

                    task_data = {
                        "title": f"Swarm: {agent_name} Task",
                        "description": payload_str,
                        "required_capabilities": caps_map.get(agent_name, ["code"]),
                        "reward": float(payload_dict.get("reward", 0.0))
                        if isinstance(payload_dict, dict) and "reward" in payload_dict
                        else 0.0,
                        "delegator_id": "system",
                    }

                    req = urllib.request.Request(
                        f"{nexus_url.rstrip('/')}/api/tasks",
                        data=json.dumps(task_data).encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {nexus_token}",
                        },
                        method="POST",
                    )

                    try:
                        resp = await loop.run_in_executor(
                            None, lambda r=req: urllib.request.urlopen(r, timeout=2.0)
                        )
                        if resp.status in (200, 201):
                            await loop.run_in_executor(
                                None, self._update_task_status, row_id, "completed"
                            )
                            logger.info("Outbox synced task: %s", task_data["title"])
                        else:
                            await loop.run_in_executor(
                                None, self._update_task_status, row_id, "failed"
                            )
                    except urllib.error.URLError as e:
                        logger.warning("Outbox sync deferred (network error): %s", e)
                        break  # Stop processing to wait for network recovery
            except Exception as e:
                logger.error("Outbox drainer error: %s", e)

    def start_guardian(self):
        if self._daemon_task:
            return
        try:
            loop = asyncio.get_running_loop()
            self._daemon_task = loop.create_task(self._drain_loop())
        except RuntimeError:
            pass


def _enqueue_swarm_task_sync(agent_name: str, payload: dict):
    """Synchronous core implementation of the Swarm Queue Dispatcher and NEXUS API sync."""
    # Sovereign SQLite Insert with Thread-Local pooling to eliminate connection/lock friction
    try:
        conn = _get_local_conn(DB_PATH, timeout=30.0)
        c = conn.cursor()
        c.execute(
            "INSERT INTO cortex_swarm_queue (timestamp, agent, payload, status) VALUES (?, ?, ?, 'pending')",
            (time.time(), agent_name, json.dumps(payload)),
        )
        conn.commit()
    except Exception as e:
        logger.error("Failed to enqueue swarm task via SQLite: %s", e)


def enqueue_swarm_task(agent_name: str, payload: dict):
    """Sovereign Swarm Queue Dispatcher. Offloads to executor if running inside an event loop to prevent event loop blocking/lag."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.run_in_executor(None, _enqueue_swarm_task_sync, agent_name, payload)
            return
    except RuntimeError:
        pass
    _enqueue_swarm_task_sync(agent_name, payload)
