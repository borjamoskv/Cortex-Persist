"""MOSKV-Aether — Data models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    CRITIQUING = "critiquing"
    TESTING = "testing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskSource(str, Enum):
    CLI = "cli"
    GITHUB = "github"
    GHOST = "ghost"


@dataclass
class AgentTask:
    """A single autonomous coding task."""

    title: str
    description: str
    repo_path: str
    source: str = TaskSource.CLI
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = TaskStatus.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    agent_id: str | None = None
    plan: str = ""
    result: str = ""
    branch: str = ""
    pr_url: str = ""
    error: str = ""
    github_issue_number: int | None = None
    github_repo: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "repo_path": self.repo_path,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "agent_id": self.agent_id,
            "plan": self.plan,
            "result": self.result,
            "branch": self.branch,
            "pr_url": self.pr_url,
            "error": self.error,
            "github_issue_number": self.github_issue_number,
            "github_repo": self.github_repo,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentTask":
        return cls(
            id=d["id"],
            title=d["title"],
            description=d["description"],
            repo_path=d["repo_path"],
            source=d.get("source", TaskSource.CLI),
            status=d.get("status", TaskStatus.PENDING),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            agent_id=d.get("agent_id"),
            plan=d.get("plan", ""),
            result=d.get("result", ""),
            branch=d.get("branch", ""),
            pr_url=d.get("pr_url", ""),
            error=d.get("error", ""),
            github_issue_number=d.get("github_issue_number"),
            github_repo=d.get("github_repo"),
        )


@dataclass
class ToolCall:
    """A parsed tool invocation from LLM output."""

    name: str
    args: dict[str, str]


@dataclass
class PlanOutput:
    """Structured plan from the Planner agent."""

    steps: list[str]
    files_to_touch: list[str]
    tests_to_run: list[str]
    summary: str = ""

    def to_prompt_str(self) -> str:
        steps = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(self.steps))
        files = ", ".join(self.files_to_touch) or "unknown"
        tests = ", ".join(self.tests_to_run) or "pytest"
        return (
            f"PLAN:\n{steps}\n\n"
            f"Files to touch: {files}\n"
            f"Tests to run: {tests}"
        )


@dataclass
class CriticOutput:
    """Review result from the Critic agent."""

    approved: bool
    issues: list[str]
    suggestions: str = ""


@dataclass
class TesterOutput:
    """Test run result from the Tester agent."""

    passed: bool
    output: str
    command: str = ""


@dataclass
class AetherAlert:
    """Alert for MoskvDaemon status reporting."""

    task_id: str
    title: str
    status: str
    message: str
