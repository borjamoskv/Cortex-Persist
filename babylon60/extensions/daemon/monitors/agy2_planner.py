# [C5-REAL] Exergy-Maximized
"""AGY2 Planner Injector Monitor.

Detects AGY2 planning mode execution (implementation_plan.md) and
automatically injects CORTEX semantic facts to resolve agent amnesia.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from babylon60.extensions.daemon.models import WorkflowAlert

logger = logging.getLogger("moskv-daemon")


class AGY2PlannerMonitor:
    """Monitors AGY2 brains for new implementation plans and injects memory."""

    def __init__(self, engine: Any, brain_dir: str = "~/.gemini/antigravity/brain") -> None:
        self.engine = engine
        self.brain_dir = Path(brain_dir).expanduser()
        self._last_mtime: dict[str, float] = {}

    async def check_async(self) -> list[WorkflowAlert]:  # type: ignore
        """Async check for modified implementation_plan.md files."""
        alerts: list[WorkflowAlert] = []
        if not self.engine:
            return alerts

        if not self.brain_dir.exists():
            return alerts

        try:
            # Glob all implementation_plan.md files in the brain directory
            for plan_file in self.brain_dir.glob("*/implementation_plan.md"):
                try:
                    mtime = plan_file.stat().st_mtime
                    last = self._last_mtime.get(str(plan_file), 0.0)
                    if mtime > last:
                        self._last_mtime[str(plan_file)] = mtime
                        # Process file
                        injected = await self._inject_context(plan_file)
                        if injected:
                            alerts.append(
                                WorkflowAlert(
                                    workflow="agy2_planning_injection",
                                    reason=f"Injected CORTEX memory into {plan_file.parent.name}",
                                    confidence="C5",
                                    priority=1,
                                    tags=["agy2", "memory_injection"],
                                )
                            )
                            # Update mtime so we don't trigger immediately again
                            self._last_mtime[str(plan_file)] = plan_file.stat().st_mtime
                except OSError:
                    continue
        except Exception as e:
            logger.error("AGY2PlannerMonitor error: %s", e)

    async def run_loop(self) -> None:
        """Run continuously as a background loop daemon."""
        logger.info("🧠 AGY2 Planner Monitor task started (interval=10s)")
        while True:
            try:
                await self.check_async()
            except Exception as e:
                logger.error("AGY2PlannerMonitor loop error: %s", e)

            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                break

    def check(self) -> list[WorkflowAlert]:
        """Synchronous wrapper for check_async."""
        try:
            return asyncio.run(self.check_async())
        except RuntimeError as e:
            if "running event loop" not in str(e):
                raise

            # If we are already inside a running event loop, we cannot use asyncio.run
            if not hasattr(self, "_bg_tasks"):
                self._bg_tasks: set = set()

            task = asyncio.ensure_future(self.check_async())
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)
            return []

    async def _inject_context(self, plan_file: Path) -> bool:
        """Read the plan, extract the goal, search memory, and inject."""
        try:
            content = plan_file.read_text(encoding="utf-8")
        except OSError:
            return False

        if "## 🧠 CORTEX Semantic Context" in content:
            return False

        # Parse Goal Description
        match = re.search(r"# Goal Description\n+(.*?)\n+##", content, re.DOTALL)
        if not match:
            return False

        goal = match.group(1).strip()
        if not goal:
            return False

        logger.info("Detected AGY2 Planning Mode. Extracting context for goal: %s...", goal[:50])

        try:
            from babylon60.memory.memory_manager import MemoryManager

            # We use the internal synchronous / async MemoryManager
            # Since MemoryManager is typically synchronous or has async variants,
            # we will just instantiate a local one or use the shared engine.
            memory = MemoryManager(engine=self.engine)
            results = await asyncio.to_thread(memory.search, query=goal, limit=5, fact_type=None)

            if not results:
                logger.debug("No CORTEX facts found for goal.")
                return False

            # Format injection
            injection = "\n\n## 🧠 CORTEX Semantic Context (Auto-Injected by C5-REAL)\n\n"
            injection += "> [!NOTE]\n> The following verified facts were retrieved from CORTEX Memory regarding your goal.\n\n"

            for fact in results:
                confidence = getattr(fact, "confidence", "Unknown")
                fact_type = getattr(fact, "fact_type", "fact").upper()
                injection += f"- **{fact_type}**: {fact.content} (Confidence: {confidence})\n"

            new_content = content + injection

            await asyncio.to_thread(plan_file.write_text, new_content, encoding="utf-8")
            logger.info("Successfully injected CORTEX context into AGY2 implementation plan.")
            return True

        except Exception as e:
            logger.error("Failed to inject context: %s", e)
            return False
