"""CORTEX Agent Runtime — Session Manager.

Persistent session management for autonomous agents.
Sessions track the full lifecycle of an autonomous task:
PLANNING → EXECUTING → VERIFYING → COMPLETED/FAILED.

Each session persists its steps, files modified, and execution logs
to SQLite for observability and resumability.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("cortex.agents.session")

__all__ = [
    "AgentSession",
    "SessionStatus",
    "SessionStep",
    "SessionStore",
    "StepStatus",
]


class SessionStatus(str, Enum):
    """Lifecycle status of an autonomous session."""

    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Status of an individual execution step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SessionStep:
    """An individual step within an autonomous session."""

    step_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    tool_name: str | None = None
    tool_args: dict[str, Any] = field(default_factory=dict)
    output: str = ""
    error: str = ""
    retries: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionStep:
        data = dict(data)
        data["status"] = StepStatus(data.get("status", "pending"))
        return cls(**data)


@dataclass
class AgentSession:
    """Persistent autonomous agent session."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    task: str = ""
    status: SessionStatus = SessionStatus.PLANNING
    steps: list[SessionStep] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def progress_pct(self) -> float:
        if not self.steps:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100

    @property
    def duration_s(self) -> float:
        return round(self.updated_at - self.created_at, 2)

    def add_log(self, message: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {message}")
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task": self.task,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "files_modified": self.files_modified,
            "logs": self.logs,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentSession:
        data = dict(data)
        data["status"] = SessionStatus(data.get("status", "planning"))
        data["steps"] = [
            SessionStep.from_dict(s) for s in data.get("steps", [])
        ]
        return cls(**data)


class SessionStore:
    """SQLite-backed persistence for autonomous sessions.

    Uses a single table with JSON serialization for session data.
    Thread-safe via connection-per-call pattern.
    """

    def __init__(self, db_path: str = "") -> None:
        import os

        self.db_path = db_path or os.environ.get(
            "CORTEX_DB_PATH", "cortex.db"
        )
        self._ensure_table()

    def _get_conn(self):
        import sqlite3

        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_table(self) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    session_id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'planning',
                    data TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_status "
                "ON agent_sessions(status)"
            )
            conn.commit()
        finally:
            conn.close()

    def create(self, task: str) -> AgentSession:
        """Create a new session in PLANNING status."""
        session = AgentSession(task=task)
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO agent_sessions "
                "(session_id, task, status, data, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session.session_id,
                    session.task,
                    session.status.value,
                    json.dumps(session.to_dict()),
                    session.created_at,
                    session.updated_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info(
            "Session created: %s (task: %.60s...)",
            session.session_id,
            task,
        )
        return session

    def update(self, session: AgentSession) -> None:
        """Persist current session state."""
        session.updated_at = time.time()
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE agent_sessions SET "
                "status = ?, data = ?, updated_at = ? "
                "WHERE session_id = ?",
                (
                    session.status.value,
                    json.dumps(session.to_dict()),
                    session.updated_at,
                    session.session_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, session_id: str) -> AgentSession | None:
        """Retrieve a session by ID (supports prefix match)."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT data FROM agent_sessions "
                "WHERE session_id LIKE ? ORDER BY created_at DESC LIMIT 1",
                (f"{session_id}%",),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return AgentSession.from_dict(json.loads(row[0]))
        finally:
            conn.close()

    def list_sessions(
        self,
        status: SessionStatus | None = None,
        limit: int = 50,
    ) -> list[AgentSession]:
        """List sessions, optionally filtered by status."""
        conn = self._get_conn()
        try:
            if status is not None:
                cursor = conn.execute(
                    "SELECT data FROM agent_sessions "
                    "WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status.value, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT data FROM agent_sessions "
                    "ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()
            return [AgentSession.from_dict(json.loads(r[0])) for r in rows]
        finally:
            conn.close()

    def cancel(self, session_id: str) -> bool:
        """Cancel a session. Returns True if found and cancelled."""
        session = self.get(session_id)
        if session is None:
            return False

        if session.status in (
            SessionStatus.COMPLETED,
            SessionStatus.CANCELLED,
        ):
            return False

        session.status = SessionStatus.CANCELLED
        session.add_log("Session cancelled by user")
        self.update(session)
        logger.info("Session cancelled: %s", session.session_id)
        return True

    def delete(self, session_id: str) -> bool:
        """Delete a session permanently."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM agent_sessions WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
