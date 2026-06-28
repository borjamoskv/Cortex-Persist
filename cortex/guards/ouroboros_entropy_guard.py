# [C5-REAL] Exergy-Maximized
"""
CORTEX - Ouroboros Entropy Guard (Axiom Ω₁₄: Infinite Loop Prevention).

Detects loop structures, abnormally high repetition, and task leaks/death spirals
in the active asyncio tasks running in the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import math
from typing import Any

import aiosqlite

logger = logging.getLogger("cortex.guards.ouroboros_entropy")


class OuroborosEntropyGuard:
    """Detects loop/entropy decay in the active asyncio tasks."""

    def __init__(self, max_tasks: int = 150, repetition_threshold: float = 0.8):
        self.max_tasks = max_tasks
        self.repetition_threshold = repetition_threshold

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        # 1. Active task pool check
        try:
            loop = asyncio.get_running_loop()
            all_tasks = asyncio.all_tasks(loop)
        except RuntimeError:
            # Fallback if running outside of active event loop
            all_tasks = set()

        if len(all_tasks) > self.max_tasks:
            raise ValueError(
                f"[P0] Ouroboros Entropy Guard: Async task limit exceeded ({len(all_tasks)} > {self.max_tasks}). "
                "Potential event loop death spiral / leak detected."
            )

        # 2. Loop detection in task names/coros (repetition)
        task_names = []
        for task in all_tasks:
            name = task.get_name().lower()
            try:
                coro_name = task.get_coro().__name__.lower()  # type: ignore
            except AttributeError:
                coro_name = ""
            task_names.append(f"{name}:{coro_name}")

        # Calculate Jaccard similarity/repetition ratio of task names
        if len(task_names) >= 5:
            # Group identical/near-identical task signatures
            unique_tasks = set(task_names)
            repetition_ratio = 1.0 - (len(unique_tasks) / len(task_names))
            if repetition_ratio > self.repetition_threshold:
                # Find the most repeated task name
                from collections import Counter

                most_common = Counter(task_names).most_common(1)[0]
                raise ValueError(
                    f"[P0] Ouroboros Entropy Guard: Infinite loop detected in async tasks. "
                    f"Task signature '{most_common[0]}' repeated {most_common[1]} times "
                    f"(repetition ratio {repetition_ratio:.2f} > {self.repetition_threshold})."
                )

        # 3. Content Shannon Entropy Check for incoming task payload
        if len(content) > 100:
            entropy = self._calculate_shannon_entropy(content)
            # Rejects abnormally low entropy (potential loop or repetitive garbage)
            if entropy < 1.5:
                raise ValueError(
                    f"[P0] Ouroboros Entropy Guard: Content has abnormally low Shannon entropy ({entropy:.4f}). "
                    "Potential repetitive loop content."
                )

    def _calculate_shannon_entropy(self, s: str) -> float:
        if not s:
            return 0.0
        probabilities = [float(s.count(c)) / len(s) for c in dict.fromkeys(s)]
        return -sum(p * math.log(p, 2) for p in probabilities)
