import os
import json
import time
import hashlib
import asyncio
import logging
import sqlite3

VSA_DIMENSION = 10000
DB_PATH = "/Users/borjafernandezangulo/Cortex-Persist/cortex-core/cortex_memory_vsa.db"
SWARM_QUEUE_FILE = "/tmp/cortex_swarm_queue.json"

logger = logging.getLogger("cortex.persistence")

class LedgerManager:
    """Sovereign SQLite Ledger — C5-REAL Persistent Chain."""
    def __init__(self):
        self._init_db()

    def _init_db(self):
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
        conn.commit()
        conn.close()

    def append(self, action: str, vector_id: str, yield_amount: float):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get previous hash
        c.execute("SELECT hash FROM ledger_records ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        prev_hash = row[0] if row else "GENESIS_BLOCK"
        
        timestamp = time.time()
        payload = f"{prev_hash}_{action}_{vector_id}_{yield_amount}_{timestamp}"
        block_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        c.execute("""
            INSERT INTO ledger_records (timestamp, action, vector_id, yield_amount, hash)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, action, vector_id, yield_amount, block_hash))
        
        conn.commit()
        conn.close()
        return block_hash

    def get_total_yield(self, vector_id=None):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if vector_id:
            c.execute("SELECT SUM(yield_amount) FROM ledger_records WHERE vector_id = ?", (vector_id,))
        else:
            c.execute("SELECT SUM(yield_amount) FROM ledger_records")
        res = c.fetchone()[0]
        conn.close()
        return res or 0.0

class VSAMemory:
    """Sovereign VSA Substrate — SQLite FTS5 Mapping."""
    def __init__(self):
        self._tensor = [0.0] * VSA_DIMENSION
        self._decay_rate = 0.99
        self._daemon_task = None

    def record(self, key: str, value: str):
        """Map semantic trace to both RAM tensor and Persistent SQLite FTS5."""
        # RAM Tensor Update (O(1) JIT)
        ctx_string = f"{key}:{value}"
        idx = int(hashlib.sha256(ctx_string.encode('utf-8')).hexdigest(), 16) % VSA_DIMENSION
        self._tensor[idx] += 1.0
        
        # Persistent SQLite Update (Axiom Ω₁)
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            ki_id = f"vsa_{int(time.time())}_{idx}"
            c.execute("INSERT INTO cortex_knowledge (ki_id, summary, content) VALUES (?, ?, ?)",
                      (ki_id, key, value))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"VSA SQLite Record Failure: {e}")

    async def _decay_loop(self):
        while True:
            await asyncio.sleep(60)
            for i in range(VSA_DIMENSION):
                if self._tensor[i] > 0.001:
                    self._tensor[i] *= self._decay_rate
                else:
                    self._tensor[i] = 0.0

    def start_glia(self):
        if not self._daemon_task:
            self._daemon_task = asyncio.create_task(self._decay_loop())

def enqueue_swarm_task(agent_name: str, payload: dict):
    """Sovereign Swarm Queue Dispatcher."""
    if not os.path.exists(SWARM_QUEUE_FILE):
        data = {"pending_tasks": []}
    else:
        with open(SWARM_QUEUE_FILE) as f:
            try:
                data = json.load(f)
            except:
                data = {"pending_tasks": []}
                
    data["pending_tasks"].append({
        "timestamp": time.time(),
        "agent": agent_name,
        "payload": payload
    })
    
    with open(SWARM_QUEUE_FILE, "w") as f:
        json.dump(data, f, indent=2)
