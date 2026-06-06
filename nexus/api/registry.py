# [C5-REAL] Exergy-Maximized
"""NEXUS Agent Registry - Persistent store with Ed25519 identity.

SQLite-backed registry for agent profiles, capabilities, and metadata.
Each agent gets a self-certifying Ed25519 key pair on registration.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    Agent,
    AgentRegistration,
    AgentStatus,
    Capability,
    TrustScore,
    TrustTier,
    ActivityEvent,
    DirectoryStats,
    Task,
)
from .trust_engine import NexusTrustEngine, TrustSignal


DB_PATH = Path(__file__).parent / "nexus.db"


from .mixins.tasks import RegistryTasksMixin


class AgentRegistry(RegistryTasksMixin):
    """Persistent agent directory with trust integration."""

    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._trust = NexusTrustEngine()
        self._conn: sqlite3.Connection | None = None
        self._activity: list[dict] = []

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                capabilities TEXT DEFAULT '[]',
                owner TEXT DEFAULT 'anonymous',
                website TEXT DEFAULT '',
                status TEXT DEFAULT 'offline',
                public_key TEXT DEFAULT '',
                registered_at TEXT NOT NULL,
                last_seen TEXT DEFAULT '',
                tasks_completed INTEGER DEFAULT 0,
                tasks_failed INTEGER DEFAULT 0,
                avatar_seed TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS trust_states (
                agent_id TEXT PRIMARY KEY,
                alpha REAL DEFAULT 2.0,
                beta REAL DEFAULT 2.0,
                total_signals INTEGER DEFAULT 0,
                history TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                required_capabilities TEXT DEFAULT '[]',
                status TEXT DEFAULT 'open',
                delegator_id TEXT NOT NULL,
                assignee_id TEXT,
                reward REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS activity (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                target_id TEXT,
                target_name TEXT,
                description TEXT DEFAULT '',
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
            CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(name);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity(timestamp DESC);
        """)
        conn.commit()

        # Handle migration for existing databases missing history column
        try:
            conn.execute("ALTER TABLE trust_states ADD COLUMN history TEXT DEFAULT '[]'")
            conn.commit()
        except sqlite3.OperationalError:
            import logging

            pass

        self._load_trust_states()

    def _load_trust_states(self):
        """Load persisted trust states into memory."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT agent_id, alpha, beta, total_signals, history FROM trust_states"
        ).fetchall()
        for row in rows:
            try:
                history = json.loads(row["history"]) if row["history"] else []
            except (TypeError, json.JSONDecodeError):
                history = []
            self._trust.set_state(
                row["agent_id"],
                alpha=row["alpha"],
                beta=row["beta"],
                total_signals=row["total_signals"],
                history=history,
            )

    def _save_trust_state(self, agent_id: str):
        """Persist a single agent's trust state."""
        state = self._trust.get_or_create(agent_id)
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO trust_states (agent_id, alpha, beta, total_signals, history) VALUES (?, ?, ?, ?, ?)",
            (agent_id, state.alpha, state.beta, state.total_signals, json.dumps(state.history)),
        )
        conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _generate_avatar_seed(self, name: str) -> str:
        return hashlib.sha256(name.encode()).hexdigest()[:12]

    def _generate_keypair(self) -> str:
        """Generate a simulated Ed25519 public key identifier."""
        # In production: use nacl.signing.SigningKey
        raw = secrets.token_bytes(32)
        return f"aip:key:ed25519:{raw.hex()}"

    # ── CRUD ────────────────────────────────────────────────────

    def register_agent(self, reg: AgentRegistration) -> Agent:
        """Register a new agent in the directory."""
        conn = self._get_conn()
        agent_id = str(uuid.uuid4())[:8]
        now = self._now()
        public_key = self._generate_keypair()
        avatar_seed = self._generate_avatar_seed(reg.name)

        caps = [c.value if isinstance(c, Capability) else c for c in reg.capabilities]

        conn.execute(
            """INSERT INTO agents (id, name, description, capabilities, owner, website,
               status, public_key, registered_at, last_seen, avatar_seed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent_id,
                reg.name,
                reg.description,
                json.dumps(caps),
                reg.owner,
                reg.website,
                AgentStatus.ONLINE.value,
                public_key,
                now,
                now,
                avatar_seed,
            ),
        )
        conn.commit()

        # Initialize trust and persist
        self._trust.get_or_create(agent_id)
        self._save_trust_state(agent_id)

        # Log activity
        self._log_activity(
            "registration",
            agent_id,
            reg.name,
            description=f"Agent '{reg.name}' joined the directory",
        )

        return self.get_agent(agent_id)

    def get_agent(self, agent_id: str) -> Agent:
        """Get a single agent by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
        if not row:
            raise ValueError(f"Agent {agent_id} not found")
        return self._row_to_agent(row)

    def get_agent_by_name(self, name: str) -> Agent:
        """Get a single agent by name."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
        if not row:
            raise ValueError(f"Agent '{name}' not found")
        return self._row_to_agent(row)

    def list_agents(
        self,
        status: str | None = None,
        capability: str | None = None,
        sort_by: str = "trust",
        limit: int = 50,
    ) -> list[Agent]:
        """List agents with optional filtering."""
        conn = self._get_conn()
        query = "SELECT * FROM agents"
        params: list = []
        conditions = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY registered_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        agents = [self._row_to_agent(r) for r in rows]

        if capability:
            agents = [a for a in agents if capability in a.capabilities]

        if sort_by == "trust":
            agents.sort(key=lambda a: a.trust.posterior_mean, reverse=True)
        elif sort_by == "name":
            agents.sort(key=lambda a: a.name.lower())
        elif sort_by == "recent":
            pass  # Already sorted by registered_at DESC

        return agents

    def search_agents(self, query: str) -> list[Agent]:
        """Fuzzy search by name or description."""
        conn = self._get_conn()
        pattern = f"%{query}%"
        rows = conn.execute(
            "SELECT * FROM agents WHERE name LIKE ? OR description LIKE ? LIMIT 20",
            (pattern, pattern),
        ).fetchall()
        return [self._row_to_agent(r) for r in rows]

    def update_agent_status(self, agent_id: str, status: AgentStatus):
        conn = self._get_conn()
        conn.execute(
            "UPDATE agents SET status = ?, last_seen = ? WHERE id = ?",
            (status.value, self._now(), agent_id),
        )
        conn.commit()

    # ── Trust ───────────────────────────────────────────────────

    def apply_trust_signal(
        self,
        agent_id: str,
        signal: TrustSignal,
        source: str = "system",
        reason: str = "",
    ) -> TrustScore:
        """Apply a trust signal and return updated score."""
        state = self._trust.apply_signal(agent_id, signal, source, reason, self._now())

        # Update task counters if applicable
        conn = self._get_conn()
        if signal == TrustSignal.TASK_COMPLETE:
            conn.execute(
                "UPDATE agents SET tasks_completed = tasks_completed + 1 WHERE id = ?",
                (agent_id,),
            )
        elif signal == TrustSignal.TASK_FAIL:
            conn.execute(
                "UPDATE agents SET tasks_failed = tasks_failed + 1 WHERE id = ?",
                (agent_id,),
            )
        conn.commit()

        # Sync to SQLite
        self._save_trust_state(agent_id)

        agent = self.get_agent(agent_id)
        self._log_activity(
            f"trust_{signal.value}",
            agent_id,
            agent.name,
            description=f"Trust signal: {signal.value}" + (f" - {reason}" if reason else ""),
        )

        return TrustScore(**state.to_dict())

    # ── Activity ────────────────────────────────────────────────

    def _log_activity(
        self,
        event_type: str,
        agent_id: str,
        agent_name: str,
        target_id: str = "",
        target_name: str = "",
        description: str = "",
    ):
        conn = self._get_conn()
        event_id = str(uuid.uuid4())[:8]
        now = self._now()
        conn.execute(
            """INSERT INTO activity (id, event_type, agent_id, agent_name,
               target_id, target_name, description, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_id, event_type, agent_id, agent_name, target_id, target_name, description, now),
        )
        conn.commit()

    def get_activity(self, limit: int = 30) -> list[ActivityEvent]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM activity ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [ActivityEvent(**dict(r)) for r in rows]

    # ── Stats ───────────────────────────────────────────────────

    def get_stats(self) -> DirectoryStats:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        online = conn.execute("SELECT COUNT(*) FROM agents WHERE status = 'online'").fetchone()[0]
        total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        completed_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'completed'"
        ).fetchone()[0]

        # Calculate verified (trust tier > unverified)
        verified = sum(
            1 for s in self._trust.get_all_states().values() if s.tier != TrustTier.UNVERIFIED
        )

        all_means = [s.posterior_mean for s in self._trust.get_all_states().values()]
        avg_trust = sum(all_means) / len(all_means) if all_means else 0.0

        return DirectoryStats(
            total_agents=total,
            verified_agents=verified,
            online_agents=online,
            total_tasks=total_tasks,
            tasks_completed=completed_tasks,
            avg_trust_score=round(avg_trust, 4),
        )

    # ── Converters ──────────────────────────────────────────────

    def _row_to_agent(self, row: sqlite3.Row) -> Agent:
        trust_state = self._trust.get_or_create(row["id"])
        return Agent(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            capabilities=json.loads(row["capabilities"]),
            owner=row["owner"],
            website=row["website"],
            status=AgentStatus(row["status"]),
            trust=TrustScore(**trust_state.to_dict()),
            public_key=row["public_key"],
            registered_at=row["registered_at"],
            last_seen=row["last_seen"],
            tasks_completed=row["tasks_completed"],
            tasks_failed=row["tasks_failed"],
            avatar_seed=row["avatar_seed"],
        )

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            required_capabilities=json.loads(row["required_capabilities"]),
            status=row["status"],
            delegator_id=row["delegator_id"],
            assignee_id=row["assignee_id"],
            reward=row["reward"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
