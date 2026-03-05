"""MOSKV-Jules — Autonomous background AI coding agent.

Jules-like agent that picks up coding tasks (GitHub Issues, CORTEX Ghosts,
or CLI input), runs a 4-agent loop (Planner→Executor→Critic→Tester) in a
local sandbox, and delivers a Git branch + optional PR.

Usage::

    from cortex.jules import JulesAgent, TaskQueue

    queue = TaskQueue()
    queue.enqueue(AgentTask(
        id="abc123",
        title="Add docstrings",
        description="Add module-level docstrings to cortex/llm/quota.py",
        repo_path="/Users/borjamoskv/cortex",
        source="cli",
    ))

    agent = JulesAgent()
    agent.run_task(queue.pop_next())
"""

from cortex.jules.models import AgentTask, TaskStatus
from cortex.jules.queue import TaskQueue
from cortex.jules.runner import JulesAgent
from cortex.jules.daemon import JulesDaemon, JulesMonitor

__all__ = [
    "AgentTask",
    "TaskStatus",
    "TaskQueue",
    "JulesAgent",
    "JulesDaemon",
    "JulesMonitor",
]
