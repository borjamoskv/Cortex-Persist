# [C5-REAL] Exergy-Maximized
from __future__ import annotations
import json
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from nexus.api.models import Task, TaskCreate, Capability, AgentStatus
from nexus.api.trust_engine import TrustSignal


class RegistryTasksMixin:
    # ── Tasks ───────────────────────────────────────────────────

    def create_task(self, task: TaskCreate) -> Task:
        conn = self._get_conn()
        task_id = str(uuid.uuid4())[:8]
        now = self._now()
        caps = [c.value if isinstance(c, Capability) else c for c in task.required_capabilities]

        conn.execute(
            """INSERT INTO tasks (id, title, description, required_capabilities,
               status, delegator_id, reward, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                task.title,
                task.description,
                json.dumps(caps),
                "open",
                task.delegator_id,
                task.reward,
                now,
            ),
        )
        conn.commit()

        self._log_activity(
            "task_created",
            task.delegator_id,
            "system",
            description=f"New task: {task.title}",
        )

        return self._get_task(task_id)

    def list_tasks(self, status: str | None = None, limit: int = 20) -> list[Task]:
        conn = self._get_conn()
        if status:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task by ID."""
        return self._get_task(task_id)

    def _get_task(self, task_id: str) -> Task:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise ValueError(f"Task {task_id} not found")
        return self._row_to_task(row)

    def assign_task(self, task_id: str, assignee_id: str) -> Task:
        """Assign a task to an agent."""
        agent = self.get_agent(assignee_id)
        task = self._get_task(task_id)

        if task.status != "open":
            raise ValueError(f"Task {task_id} is not open (status: {task.status})")

        conn = self._get_conn()
        conn.execute(
            "UPDATE tasks SET status = 'assigned', assignee_id = ? WHERE id = ?",
            (assignee_id, task_id),
        )
        conn.commit()

        # Update agent status to busy
        self.update_agent_status(assignee_id, AgentStatus.BUSY)

        self._log_activity(
            "task_assigned",
            assignee_id,
            agent.name,
            target_id=task_id,
            target_name=task.title,
            description=f"Task '{task.title}' assigned to agent '{agent.name}'",
        )

        return self._get_task(task_id)

    def complete_task(self, task_id: str) -> Task:
        """Mark a task as completed and apply trust signal."""
        task = self._get_task(task_id)
        if task.status != "assigned":
            raise ValueError(f"Task {task_id} is not assigned (status: {task.status})")
        if not task.assignee_id:
            raise ValueError(f"Task {task_id} has no assignee")

        now = self._now()
        conn = self._get_conn()
        conn.execute(
            "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, task_id),
        )
        conn.commit()

        # Apply trust signal TASK_COMPLETE to the assignee
        self.apply_trust_signal(
            task.assignee_id,
            TrustSignal.TASK_COMPLETE,
            source="system",
            reason=f"Successfully completed task '{task.title}'",
        )

        # Revert agent status to online (since task is done)
        self.update_agent_status(task.assignee_id, AgentStatus.ONLINE)

        return self._get_task(task_id)

    def fail_task(self, task_id: str, reason: str = "") -> Task:
        """Mark a task as failed and apply trust signal."""
        task = self._get_task(task_id)
        if task.status != "assigned":
            raise ValueError(f"Task {task_id} is not assigned (status: {task.status})")
        if not task.assignee_id:
            raise ValueError(f"Task {task_id} has no assignee")

        now = self._now()
        conn = self._get_conn()
        conn.execute(
            "UPDATE tasks SET status = 'failed', completed_at = ? WHERE id = ?",
            (now, task_id),
        )
        conn.commit()

        # Apply trust signal TASK_FAIL to the assignee
        self.apply_trust_signal(
            task.assignee_id,
            TrustSignal.TASK_FAIL,
            source="system",
            reason=f"Failed task '{task.title}'" + (f": {reason}" if reason else ""),
        )

        # Revert agent status to online
        self.update_agent_status(task.assignee_id, AgentStatus.ONLINE)

        return self._get_task(task_id)
