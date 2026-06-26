from __future__ import annotations

import os
import sqlite3

from .models import SwarmEvent


from cortex.database.core import CortexConnection

class SwarmLedger:
    def __init__(self, path: str | None = None):
        if path is None:
            path = os.getenv("CORTEX_SWARM_DB_PATH", "cortex_swarm.db")
        self.conn = sqlite3.connect(path, timeout=10, check_same_thread=False, factory=CortexConnection)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init()

    def _init(self):
        import os
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path) as f:
            if hasattr(self.conn, "authorize_causal_writes"):
                self.conn.authorize_causal_writes()
            try:
                self.conn.executescript(f.read())
            finally:
                if hasattr(self.conn, "revoke_causal_writes"):
                    self.conn.revoke_causal_writes()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def append(self, event: SwarmEvent) -> str:
        r = event.to_record()
        
        if hasattr(self.conn, "authorize_causal_writes"):
            self.conn.authorize_causal_writes()
        try:
            self.conn.execute(
                """
                INSERT INTO swarm_events (
                    event_id, timestamp, input_hash, registry_hash,
                    task, selected_agent, routing_payload,
                    deterministic_signature, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    r["event_id"],
                    r["timestamp"],
                    r["input_hash"],
                    r["registry_hash"],
                    r["task"],
                    r["selected_agent"],
                    r["routing_payload"],
                    r["deterministic_signature"],
                    r["version"],
                ),
            )
            self.conn.commit()
        finally:
            if hasattr(self.conn, "revoke_causal_writes"):
                self.conn.revoke_causal_writes()
        return r["event_id"]

    # ------------------------------------------------------------------
    # Read / Replay
    # ------------------------------------------------------------------

    def replay(self, task: str) -> list[dict]:
        """All events for a task, chronological order."""
        cur = self.conn.execute(
            "SELECT * FROM swarm_events WHERE task = ? ORDER BY id ASC", (task,)
        )
        return [dict(row) for row in cur.fetchall()]

    def replay_from_timestamp(self, ts: str, task: str | None = None) -> list[dict]:
        """
        Returns all events at or after `ts` (ISO-8601).
        Optionally filtered by task.
        """
        if task:
            cur = self.conn.execute(
                "SELECT * FROM swarm_events WHERE timestamp >= ? AND task = ? ORDER BY id ASC",
                (ts, task),
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM swarm_events WHERE timestamp >= ? ORDER BY id ASC", (ts,)
            )
        return [dict(row) for row in cur.fetchall()]

    def get_event(self, event_id: str) -> dict | None:
        """Fetch a single event by its deterministic event_id."""
        cur = self.conn.execute("SELECT * FROM swarm_events WHERE event_id = ?", (event_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def all_events(self) -> list[dict]:
        """Full ledger, chronological."""
        cur = self.conn.execute("SELECT * FROM swarm_events ORDER BY id ASC")
        return [dict(row) for row in cur.fetchall()]
