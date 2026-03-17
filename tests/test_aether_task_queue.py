"""Tests for cortex.aether.queue — SQLite-backed task queue.

Uses tmp_path for isolated database per test. No network, no LLM.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.extensions.aether.models import AgentTask, TaskStatus
from cortex.extensions.aether.queue import TaskQueue


@pytest.fixture
def queue(tmp_path: Path) -> TaskQueue:
    """Create a TaskQueue backed by a temp SQLite database."""
    return TaskQueue(db_path=tmp_path / "test_aether.db")


def _make_task(**overrides) -> AgentTask:
    """Factory for creating test tasks with sensible defaults."""
    defaults = {
        "title": "Test task",
        "description": "A test task for the queue",
        "repo_path": "/tmp/test-repo",
    }
    defaults.update(overrides)
    return AgentTask(**defaults)


# ─── Enqueue ─────────────────────────────────────────────────────────


class TestEnqueue:
    def test_enqueue_returns_task(self, queue: TaskQueue):
        task = _make_task()
        result = queue.enqueue(task)
        assert isinstance(result, AgentTask)
        assert result.id == task.id

    def test_enqueue_sets_pending(self, queue: TaskQueue):
        task = _make_task()
        result = queue.enqueue(task)
        assert result.status == TaskStatus.PENDING

    def test_enqueue_sets_timestamps(self, queue: TaskQueue):
        task = _make_task()
        result = queue.enqueue(task)
        assert result.created_at != ""
        assert result.updated_at != ""

    def test_enqueue_multiple_tasks(self, queue: TaskQueue):
        for i in range(5):
            queue.enqueue(_make_task(title=f"Task {i}"))
        assert queue.pending_count == 5

    def test_enqueue_duplicate_id_raises(self, queue: TaskQueue):
        task = _make_task()
        queue.enqueue(task)
        with pytest.raises(Exception):  # IntegrityError
            queue.enqueue(task)


# ─── Pop ─────────────────────────────────────────────────────────────


class TestPopNext:
    def test_pop_empty_returns_none(self, queue: TaskQueue):
        assert queue.pop_next() is None

    def test_pop_returns_oldest_pending(self, queue: TaskQueue):
        t1 = _make_task(title="First")
        t2 = _make_task(title="Second")
        queue.enqueue(t1)
        queue.enqueue(t2)

        popped = queue.pop_next()
        assert popped is not None
        assert popped.title == "First"

    def test_pop_sets_planning_status(self, queue: TaskQueue):
        queue.enqueue(_make_task())
        popped = queue.pop_next()
        assert popped is not None
        assert popped.status == TaskStatus.PLANNING

    def test_pop_is_atomic_no_double_pop(self, queue: TaskQueue):
        queue.enqueue(_make_task())
        first = queue.pop_next()
        second = queue.pop_next()
        assert first is not None
        assert second is None  # Already popped


# ─── Get ─────────────────────────────────────────────────────────────


class TestGet:
    def test_get_existing(self, queue: TaskQueue):
        task = _make_task()
        queue.enqueue(task)
        fetched = queue.get(task.id)
        assert fetched is not None
        assert fetched.id == task.id
        assert fetched.title == task.title

    def test_get_nonexistent(self, queue: TaskQueue):
        assert queue.get("nonexistent_id") is None


# ─── Update ──────────────────────────────────────────────────────────


class TestUpdate:
    def test_update_status(self, queue: TaskQueue):
        task = _make_task()
        queue.enqueue(task)
        queue.update(task.id, status=TaskStatus.EXECUTING)
        fetched = queue.get(task.id)
        assert fetched is not None
        assert fetched.status == TaskStatus.EXECUTING

    def test_update_multiple_fields(self, queue: TaskQueue):
        task = _make_task()
        queue.enqueue(task)
        queue.update(task.id, status=TaskStatus.DONE, result="All good", branch="fix/test")
        fetched = queue.get(task.id)
        assert fetched is not None
        assert fetched.status == TaskStatus.DONE
        assert fetched.result == "All good"
        assert fetched.branch == "fix/test"

    def test_update_sets_updated_at(self, queue: TaskQueue):
        task = _make_task()
        queue.enqueue(task)
        original_updated = queue.get(task.id).updated_at
        queue.update(task.id, status=TaskStatus.EXECUTING)
        new_updated = queue.get(task.id).updated_at
        assert new_updated >= original_updated

    def test_update_empty_fields_noop(self, queue: TaskQueue):
        task = _make_task()
        queue.enqueue(task)
        queue.update(task.id)  # No fields → should not raise


# ─── List ────────────────────────────────────────────────────────────


class TestListTasks:
    def test_list_all(self, queue: TaskQueue):
        for i in range(3):
            queue.enqueue(_make_task(title=f"Task {i}"))
        tasks = queue.list_tasks()
        assert len(tasks) == 3

    def test_list_filtered_by_status(self, queue: TaskQueue):
        queue.enqueue(_make_task(title="A"))
        queue.enqueue(_make_task(title="B"))
        queue.pop_next()  # Moves one to PLANNING
        pending = queue.list_tasks(status=TaskStatus.PENDING)
        planning = queue.list_tasks(status=TaskStatus.PLANNING)
        assert len(pending) == 1
        assert len(planning) == 1

    def test_list_respects_limit(self, queue: TaskQueue):
        for i in range(10):
            queue.enqueue(_make_task(title=f"Task {i}"))
        tasks = queue.list_tasks(limit=3)
        assert len(tasks) == 3

    def test_list_empty_queue(self, queue: TaskQueue):
        assert queue.list_tasks() == []


# ─── Cancel ──────────────────────────────────────────────────────────


class TestCancel:
    def test_cancel_pending_task(self, queue: TaskQueue):
        task = _make_task()
        queue.enqueue(task)
        assert queue.cancel(task.id) is True
        fetched = queue.get(task.id)
        assert fetched.status == TaskStatus.CANCELLED

    def test_cancel_nonexistent(self, queue: TaskQueue):
        assert queue.cancel("ghost_id") is False

    def test_cancel_already_done(self, queue: TaskQueue):
        task = _make_task()
        queue.enqueue(task)
        queue.update(task.id, status=TaskStatus.DONE)
        assert queue.cancel(task.id) is False  # Can't cancel done

    def test_cancel_planning_task(self, queue: TaskQueue):
        task = _make_task()
        queue.enqueue(task)
        queue.pop_next()  # Sets to PLANNING
        assert queue.cancel(task.id) is True


# ─── Pending Count ───────────────────────────────────────────────────


class TestPendingCount:
    def test_empty(self, queue: TaskQueue):
        assert queue.pending_count == 0

    def test_after_enqueue(self, queue: TaskQueue):
        queue.enqueue(_make_task())
        assert queue.pending_count == 1

    def test_after_pop(self, queue: TaskQueue):
        queue.enqueue(_make_task())
        queue.pop_next()
        assert queue.pending_count == 0
