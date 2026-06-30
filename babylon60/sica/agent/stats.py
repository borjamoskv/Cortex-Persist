# [C5-REAL] Exergy-Maximized

from typing import Any

from babylon60.sica.meta_level import MetaJudgment


class _LifetimeStats:
    """Accumulated statistics across the agent's lifetime."""

    def __init__(self) -> None:
        self.tasks_succeeded = 0
        self.tasks_failed = 0
        self.escalations = 0
        self.aborts = 0
        self.mutations = 0
        self.meta_failures = 0
        self.object_failures = 0

    def record_judgment(self, judgment: MetaJudgment) -> None:
        if judgment.is_meta_failure:
            self.meta_failures += 1
        elif judgment.failure_class is not None:
            self.object_failures += 1

    def summary(self) -> str:
        total = self.tasks_succeeded + self.tasks_failed
        rate = (self.tasks_succeeded / total * 100) if total > 0 else 0
        return (
            f"tasks={total} success={rate:.0f}% "
            f"mutations={self.mutations} "
            f"meta_failures={self.meta_failures} "
            f"escalations={self.escalations}"
        )

    def to_dict(self) -> dict[str, Any]:
        total = self.tasks_succeeded + self.tasks_failed
        return {
            "total_tasks": total,
            "succeeded": self.tasks_succeeded,
            "failed": self.tasks_failed,
            "success_rate": round(self.tasks_succeeded / total, 3) if total > 0 else 0,
            "mutations": self.mutations,
            "meta_failures": self.meta_failures,
            "object_failures": self.object_failures,
            "escalations": self.escalations,
            "aborts": self.aborts,
        }
