"""Tests for CORTEX Agent Session Manager.

Tests:
    - Session creation and persistence
    - Session listing and filtering
    - Session update and state roundtrip
    - Session cancellation
    - Prefix-match ID lookup
"""

from __future__ import annotations

import pytest

from cortex.agents.session import (
    AgentSession,
    SessionStatus,
    SessionStep,
    SessionStore,
    StepStatus,
)


@pytest.fixture
def store(tmp_path):
    """Create a SessionStore with a temporary database."""
    db_path = str(tmp_path / "test_sessions.db")
    return SessionStore(db_path=db_path)


class TestSessionStep:
    def test_step_defaults(self):
        step = SessionStep(description="Do something")
        assert step.status == StepStatus.PENDING
        assert step.retries == 0
        assert step.tool_name is None

    def test_step_roundtrip(self):
        step = SessionStep(
            description="Write file",
            tool_name="file_write",
            tool_args={"path": "/tmp/test.py", "content": "hello"},
        )
        d = step.to_dict()
        restored = SessionStep.from_dict(d)
        assert restored.description == "Write file"
        assert restored.tool_name == "file_write"
        assert restored.tool_args["path"] == "/tmp/test.py"


class TestAgentSession:
    def test_session_defaults(self):
        session = AgentSession(task="Build a feature")
        assert session.status == SessionStatus.PLANNING
        assert session.total_steps == 0
        assert session.completed_steps == 0
        assert session.progress_pct == 0.0

    def test_progress_calculation(self):
        session = AgentSession(task="test")
        session.steps = [
            SessionStep(description="a", status=StepStatus.COMPLETED),
            SessionStep(description="b", status=StepStatus.COMPLETED),
            SessionStep(description="c", status=StepStatus.PENDING),
        ]
        assert session.completed_steps == 2
        assert session.total_steps == 3
        assert session.progress_pct == pytest.approx(66.67, rel=0.01)

    def test_add_log(self):
        session = AgentSession(task="test")
        session.add_log("Step 1 started")
        assert len(session.logs) == 1
        assert "Step 1 started" in session.logs[0]

    def test_session_roundtrip(self):
        session = AgentSession(task="Complex task")
        session.steps = [
            SessionStep(description="step1", status=StepStatus.COMPLETED),
        ]
        session.files_modified = ["/tmp/a.py"]
        session.add_log("log entry")

        d = session.to_dict()
        restored = AgentSession.from_dict(d)

        assert restored.task == "Complex task"
        assert len(restored.steps) == 1
        assert restored.steps[0].status == StepStatus.COMPLETED
        assert restored.files_modified == ["/tmp/a.py"]
        assert len(restored.logs) == 1


class TestSessionStore:
    def test_create_session(self, store):
        session = store.create("Build hello world")
        assert session.status == SessionStatus.PLANNING
        assert session.task == "Build hello world"
        assert len(session.session_id) == 16

    def test_get_session(self, store):
        created = store.create("Test task")
        fetched = store.get(created.session_id)
        assert fetched is not None
        assert fetched.session_id == created.session_id
        assert fetched.task == "Test task"

    def test_get_session_prefix(self, store):
        created = store.create("Prefix test")
        # Use first 6 chars as prefix
        fetched = store.get(created.session_id[:6])
        assert fetched is not None
        assert fetched.session_id == created.session_id

    def test_get_nonexistent(self, store):
        result = store.get("nonexistent_id_123")
        assert result is None

    def test_list_sessions(self, store):
        store.create("Task A")
        store.create("Task B")
        store.create("Task C")

        sessions = store.list_sessions()
        assert len(sessions) == 3

    def test_list_sessions_filtered(self, store):
        s1 = store.create("Task A")
        s2 = store.create("Task B")

        # Update one to COMPLETED
        s1.status = SessionStatus.COMPLETED
        store.update(s1)

        planning = store.list_sessions(status=SessionStatus.PLANNING)
        completed = store.list_sessions(status=SessionStatus.COMPLETED)

        assert len(planning) == 1
        assert len(completed) == 1
        assert completed[0].session_id == s1.session_id

    def test_update_session(self, store):
        session = store.create("Update test")
        session.status = SessionStatus.EXECUTING
        session.steps = [
            SessionStep(description="step1", status=StepStatus.COMPLETED),
        ]
        session.files_modified = ["/tmp/file.py"]
        store.update(session)

        fetched = store.get(session.session_id)
        assert fetched is not None
        assert fetched.status == SessionStatus.EXECUTING
        assert len(fetched.steps) == 1
        assert fetched.files_modified == ["/tmp/file.py"]

    def test_cancel_session(self, store):
        session = store.create("Cancel test")
        result = store.cancel(session.session_id)
        assert result is True

        fetched = store.get(session.session_id)
        assert fetched is not None
        assert fetched.status == SessionStatus.CANCELLED

    def test_cancel_completed_session(self, store):
        session = store.create("Already done")
        session.status = SessionStatus.COMPLETED
        store.update(session)

        result = store.cancel(session.session_id)
        assert result is False

    def test_delete_session(self, store):
        session = store.create("Delete me")
        assert store.delete(session.session_id) is True
        assert store.get(session.session_id) is None

    def test_list_sessions_limit(self, store):
        for i in range(10):
            store.create(f"Task {i}")

        sessions = store.list_sessions(limit=5)
        assert len(sessions) == 5
