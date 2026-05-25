import os
import json
import time
import hashlib
import asyncio
import logging
import sqlite3
import fcntl

VSA_DIMENSION = 10000
DB_PATH = os.getenv(
    "CORTEX_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cortex_memory_vsa.db")
)
SWARM_QUEUE_FILE = "/tmp/cortex_swarm_queue.json"

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
        self._init_db()

    def _init_db(self):
        # Ensure database parent directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
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
            conn.commit()
        finally:
            if conn:
                conn.close()

    def append(self, action: str, vector_id: str, yield_amount: float) -> str:
        """Hash-chain new transaction to guarantee auditable tamper-evident history."""
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()

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
            conn.commit()
            return block_hash
        finally:
            if conn:
                conn.close()

    def get_total_yield(self, vector_id=None) -> float:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            if vector_id:
                c.execute(
                    "SELECT SUM(yield_amount) FROM ledger_records WHERE vector_id = ?", (vector_id,)
                )
            else:
                c.execute("SELECT SUM(yield_amount) FROM ledger_records")
            res = c.fetchone()[0]
            return res or 0.0
        finally:
            if conn:
                conn.close()


class VSAMemory:
    """L2 Sovereign Vector Symbolic Architecture (VSA) Substrate & SQLite Semantic Knowledge Base."""

    def __init__(self):
        self._tensor = [0.0] * VSA_DIMENSION
        self._decay_rate = 0.99
        self._daemon_task = None

    def record(self, key: str, value: str):
        """Map semantic trace to both RAM tensor and Persistent SQLite FTS5."""
        ctx_string = f"{key}:{value}"
        idx = int(hashlib.sha256(ctx_string.encode("utf-8")).hexdigest(), 16) % VSA_DIMENSION
        self._tensor[idx] += 1.0

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            ki_id = f"vsa_{int(time.time())}_{idx}"
            c.execute(
                "INSERT OR REPLACE INTO cortex_knowledge (ki_id, summary, content) VALUES (?, ?, ?)",
                (ki_id, key, value),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"VSA SQLite Record Failure: {e}")
        finally:
            if conn:
                conn.close()

    async def _decay_loop(self):
        """Periodically decay high-dimensional state space to model biological memory loss."""
        while True:
            await asyncio.sleep(60)
            for i in range(VSA_DIMENSION):
                if self._tensor[i] > 0.001:
                    self._tensor[i] *= self._decay_rate
                else:
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


class HybridPersistenceManager:
    """
    Sovereign Hybrid Persistence Manager.
    Integrates L1 (RAM Context), L2 (Semantic VSA/SQLite), and L3 (Cryptographic Audit Ledger).
    """

    def __init__(self):
        self.l1 = ContextCache()
        self.l2 = VSAMemory()
        self.l3 = LedgerManager()
        self.l2.start_glia()


def enqueue_swarm_task(agent_name: str, payload: dict):
    """Sovereign Swarm Queue Dispatcher with POSIX file locking."""
    # Ensure queue file exists before locking
    if not os.path.exists(SWARM_QUEUE_FILE):
        try:
            with open(SWARM_QUEUE_FILE, "w") as f:
                json.dump({"pending_tasks": []}, f)
        except OSError:
            pass

    try:
        with open(SWARM_QUEUE_FILE, "r+") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    data = json.load(f)
                except Exception:
                    data = {"pending_tasks": []}

                data["pending_tasks"].append(
                    {"timestamp": time.time(), "agent": agent_name, "payload": payload}
                )

                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Failed to enqueue swarm task: {e}")
