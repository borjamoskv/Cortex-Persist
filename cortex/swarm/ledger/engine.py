import sqlite3
from .models import SwarmEvent


class SwarmLedger:
    def __init__(self, path="cortex_swarm.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        with open("cortex/swarm/ledger/schema.sql") as f:
            self.conn.executescript(f.read())

    def append(self, event: SwarmEvent):
        r = event.to_record()

        self.conn.execute("""
            INSERT INTO swarm_events (
                event_id, timestamp, input_hash, registry_hash,
                task, selected_agent, routing_payload,
                deterministic_signature, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["event_id"],
            r["timestamp"],
            r["input_hash"],
            r["registry_hash"],
            r["task"],
            r["selected_agent"],
            r["routing_payload"],
            r["deterministic_signature"],
            r["version"],
        ))

        self.conn.commit()
        return r["event_id"]

    def replay(self, task: str):
        cur = self.conn.execute(
            "SELECT * FROM swarm_events WHERE task = ? ORDER BY id ASC",
            (task,)
        )
        return [dict(row) for row in cur.fetchall()]
