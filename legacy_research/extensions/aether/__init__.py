# [C5-REAL] Exergy-Maximized
"""MOSKV-Aether - Autonomous background AI coding agent.

Autonomous agent that picks up coding tasks (GitHub Issues, CORTEX Ghosts,
or CLI input), runs a 4-agent loop (Planner→Executor→Critic→Tester) in a
local sandbox, and delivers a Git branch + optional PR.

Usage::

    from legacy_research.extensions.aether import AetherAgent, TaskQueue

    queue = TaskQueue()
    queue.enqueue(AgentTask(
        id="abc123",
        title="Add docstrings",
        description="Add module-level docstrings to cortex/llm/quota.py",
        repo_path="~/cortex",
        source="cli",
    ))

    agent = AetherAgent()
    agent.run_task(queue.pop_next())
"""

from legacy_research.extensions.aether.daemon import AetherDaemon, AetherMonitor
from legacy_research.extensions.aether.models import AgentTask, TaskStatus
from legacy_research.extensions.aether.queue import TaskQueue
from legacy_research.extensions.aether.runner import AetherAgent

__all__ = [
    "AetherAgent",
    "AetherDaemon",
    "AetherMonitor",
    "AgentTask",
    "TaskQueue",
    "TaskStatus",
]
