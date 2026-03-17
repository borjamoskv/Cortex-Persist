"""Tests for cortex.aether.models — Pure data model validation.

No I/O, no network, no database. Pure unit tests.
"""

from __future__ import annotations

from cortex.extensions.aether.models import (
    AetherAlert,
    AgentTask,
    CriticOutput,
    PlanOutput,
    TaskSource,
    TaskStatus,
    TesterOutput,
    ToolCall,
)

# ─── TaskStatus ──────────────────────────────────────────────────────


class TestTaskStatus:
    def test_enum_values_are_strings(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.DONE == "done"
        assert TaskStatus.FAILED == "failed"

    def test_all_statuses_exist(self):
        expected = {
            "pending",
            "planning",
            "executing",
            "critiquing",
            "testing",
            "done",
            "failed",
            "cancelled",
        }
        actual = {s.value for s in TaskStatus}
        assert actual == expected

    def test_status_is_str_subclass(self):
        assert isinstance(TaskStatus.PENDING, str)


# ─── TaskSource ──────────────────────────────────────────────────────


class TestTaskSource:
    def test_source_values(self):
        assert TaskSource.CLI == "cli"
        assert TaskSource.GITHUB == "github"
        assert TaskSource.GHOST == "ghost"


# ─── AgentTask ───────────────────────────────────────────────────────


class TestAgentTask:
    def test_creation_defaults(self):
        task = AgentTask(
            title="Fix bug",
            description="Fix the null pointer",
            repo_path="/tmp/repo",
        )
        assert task.title == "Fix bug"
        assert task.status == TaskStatus.PENDING
        assert task.source == TaskSource.CLI
        assert task.plan == ""
        assert task.error == ""
        assert task.github_issue_number is None
        assert len(task.id) == 12  # uuid hex[:12]

    def test_unique_ids(self):
        t1 = AgentTask(title="A", description="a", repo_path="/tmp")
        t2 = AgentTask(title="B", description="b", repo_path="/tmp")
        assert t1.id != t2.id

    def test_to_dict_roundtrip(self):
        task = AgentTask(
            title="Test roundtrip",
            description="Verify serialization",
            repo_path="/tmp/repo",
            source=TaskSource.GITHUB,
            github_issue_number=42,
            github_repo="org/repo",
        )
        d = task.to_dict()
        restored = AgentTask.from_dict(d)
        assert restored.title == task.title
        assert restored.description == task.description
        assert restored.repo_path == task.repo_path
        assert restored.source == task.source
        assert restored.github_issue_number == 42
        assert restored.github_repo == "org/repo"

    def test_to_dict_contains_all_fields(self):
        task = AgentTask(title="T", description="D", repo_path="/tmp")
        d = task.to_dict()
        required_keys = {
            "id",
            "title",
            "description",
            "repo_path",
            "source",
            "status",
            "created_at",
            "updated_at",
            "plan",
            "result",
            "branch",
            "pr_url",
            "error",
            "agent_id",
            "github_issue_number",
            "github_repo",
        }
        assert required_keys <= set(d.keys())

    def test_from_dict_with_minimal_fields(self):
        d = {
            "id": "abc123",
            "title": "Minimal",
            "description": "test",
            "repo_path": "/tmp",
        }
        task = AgentTask.from_dict(d)
        assert task.id == "abc123"
        assert task.status == TaskStatus.PENDING
        assert task.source == TaskSource.CLI

    def test_from_dict_preserves_status(self):
        d = {
            "id": "x",
            "title": "T",
            "description": "D",
            "repo_path": "/tmp",
            "status": TaskStatus.DONE,
        }
        task = AgentTask.from_dict(d)
        assert task.status == TaskStatus.DONE


# ─── PlanOutput ──────────────────────────────────────────────────────


class TestPlanOutput:
    def test_to_prompt_str_format(self):
        plan = PlanOutput(
            steps=["Read file", "Edit function", "Run tests"],
            files_to_touch=["main.py"],
            tests_to_run=["pytest tests/"],
            summary="Simple fix",
        )
        output = plan.to_prompt_str()
        assert "PLAN:" in output
        assert "1. Read file" in output
        assert "2. Edit function" in output
        assert "3. Run tests" in output
        assert "main.py" in output
        assert "pytest tests/" in output

    def test_empty_plan(self):
        plan = PlanOutput(steps=[], files_to_touch=[], tests_to_run=[])
        output = plan.to_prompt_str()
        assert "unknown" in output  # No files → "unknown"
        assert "pytest" in output  # No tests → "pytest"


# ─── CriticOutput ────────────────────────────────────────────────────


class TestCriticOutput:
    def test_approved(self):
        c = CriticOutput(approved=True, issues=[])
        assert c.approved is True
        assert c.issues == []

    def test_rejected_with_issues(self):
        c = CriticOutput(
            approved=False,
            issues=["Missing docstring", "No error handling"],
            suggestions="Add try/except",
        )
        assert c.approved is False
        assert len(c.issues) == 2
        assert c.suggestions == "Add try/except"


# ─── TesterOutput ────────────────────────────────────────────────────


class TestTesterOutput:
    def test_passed(self):
        t = TesterOutput(passed=True, output="All tests passed")
        assert t.passed is True

    def test_failed_with_output(self):
        t = TesterOutput(passed=False, output="FAILED: test_foo", command="pytest")
        assert t.passed is False
        assert t.command == "pytest"


# ─── ToolCall ────────────────────────────────────────────────────────


class TestToolCall:
    def test_creation(self):
        tc = ToolCall(name="read_file", args={"path": "/tmp/x.py"})
        assert tc.name == "read_file"
        assert tc.args["path"] == "/tmp/x.py"

    def test_empty_args(self):
        tc = ToolCall(name="list_files", args={})
        assert tc.args == {}


# ─── AetherAlert ──────────────────────────────────────────────────────


class TestAetherAlert:
    def test_creation(self):
        alert = AetherAlert(
            task_id="abc",
            title="Task done",
            status="done",
            message="Completed successfully",
        )
        assert alert.task_id == "abc"
        assert alert.status == "done"
