"""MOSKV-Jules — CLI commands.

Registered as `cortex jules` subcommand group.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cortex.jules.models import AgentTask, TaskSource
from cortex.jules.queue import TaskQueue


def _make_queue() -> TaskQueue:
    return TaskQueue()


def cmd_enqueue(args: argparse.Namespace) -> None:
    queue = _make_queue()
    task = AgentTask(
        title=args.title,
        description=args.description or args.title,
        repo_path=str(Path(args.repo).resolve()),
        source=TaskSource.CLI,
    )
    queue.enqueue(task)
    print(f"✅ Enqueued task [{task.id}]: {task.title}")
    print(f"   Repo: {task.repo_path}")


def cmd_status(args: argparse.Namespace) -> int:
    queue = _make_queue()
    tasks = queue.list_tasks(limit=20)
    if not tasks:
        print("No tasks found.")
        return 0

    _STATUS_EMOJI = {
        "pending": "⏳",
        "planning": "🧠",
        "executing": "⚙️",
        "critiquing": "🔍",
        "testing": "🧪",
        "done": "✅",
        "failed": "❌",
        "cancelled": "🚫",
    }
    header = f"{'ID':<14} {'STATUS':<12} {'TITLE':<40} {'BRANCH':<25}"
    print(header)
    print("-" * len(header))
    for t in tasks:
        emoji = _STATUS_EMOJI.get(t.status, "❓")
        title = t.title[:38] + ".." if len(t.title) > 40 else t.title
        branch = t.branch[:23] + ".." if len(t.branch) > 25 else t.branch
        print(f"{t.id:<14} {emoji}{t.status:<11} {title:<40} {branch:<25}")
    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    queue = _make_queue()
    task = queue.get(args.task_id)
    if task is None:
        print(f"Task [{args.task_id}] not found.")
        return 1
    print(f"Task [{task.id}] — {task.title}")
    print(f"Status  : {task.status}")
    print(f"Branch  : {task.branch or 'none'}")
    print(f"Created : {task.created_at}")
    print(f"Updated : {task.updated_at}")
    if task.plan:
        print(f"\n── PLAN ──\n{task.plan}")
    if task.result:
        print(f"\n── RESULT ──\n{task.result[:2000]}")
    if task.error:
        print(f"\n── ERROR ──\n{task.error}")
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    queue = _make_queue()
    if queue.cancel(args.task_id):
        print(f"🚫 Cancelled task [{args.task_id}]")
        return 0
    else:
        print(f"Task [{args.task_id}] not found or already terminal.")
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Immediately run the next pending task (foreground, for testing)."""
    from cortex.jules.runner import JulesAgent

    queue = _make_queue()
    task = queue.pop_next()
    if task is None:
        print("No pending tasks.")
        return 0

    print(f"🤖 Running task [{task.id}]: {task.title}")
    agent = JulesAgent(llm_provider=getattr(args, "provider", "qwen"))
    result = agent.run_task_sync(task, queue)
    print(f"\n{'✅' if result.status == 'done' else '❌'} Task {result.status}")
    if result.branch:
        print(f"Branch: {result.branch}")
    if result.error:
        print(f"Error: {result.error}")
    return 0 if result.status == "done" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cortex jules",
        description="MOSKV-Jules — Autonomous background AI coding agent",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # enqueue
    p_enqueue = sub.add_parser("enqueue", help="Add a task to the queue")
    p_enqueue.add_argument("repo", help="Path to the git repository")
    p_enqueue.add_argument("title", help="Short task title")
    p_enqueue.add_argument("--description", "-d", default="", help="Full task description")
    p_enqueue.set_defaults(func=cmd_enqueue)

    # status
    p_status = sub.add_parser("status", help="List all tasks")
    p_status.set_defaults(func=cmd_status)

    # logs
    p_logs = sub.add_parser("logs", help="Show task logs")
    p_logs.add_argument("task_id", help="Task ID")
    p_logs.set_defaults(func=cmd_logs)

    # cancel
    p_cancel = sub.add_parser("cancel", help="Cancel a pending task")
    p_cancel.add_argument("task_id", help="Task ID")
    p_cancel.set_defaults(func=cmd_cancel)

    # run (foreground)
    p_run = sub.add_parser("run", help="Run next pending task in foreground")
    p_run.add_argument("--provider", default="qwen", help="LLM provider")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
