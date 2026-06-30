#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""CORTEX Level 3 Copilot - End-to-End Integration Demo.

Reality Level: C5-REAL

Demonstrates the full copilot flow:
  1. Human types code → Context captured
  2. CopilotAgent observes → Generates suggestions
  3. Human reviews → Accepts/rejects
  4. Telemetry recorded → Acceptance rate tracked

Run:
    cd cortex-persist
    .venv/bin/python examples/copilot_demo.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from babylon60.agents.builtins.copilot_agent import (
    CopilotAgent,
    create_copilot_agent,
)
from babylon60.agents.copilot_contracts import (
    CopilotContextPayload,
    CursorContext,
    ProjectContext,
    SuggestionStatus,
    SuggestionVerdict,
)
from babylon60.agents.message_schema import MessageKind, new_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-30s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("copilot.demo")


# ── Mock Bus (in-process) ─────────────────────────────────────────


class DemoBus:
    """Simple in-process message bus for demo purposes."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self.log: list[dict] = []

    async def send(self, msg) -> None:
        self.log.append({"to": msg.recipient, "kind": msg.kind.value})
        q = self._queues.setdefault(msg.recipient, asyncio.Queue())
        await q.put(msg)

    async def receive(self, agent_id: str, timeout: float = 1.0) -> None:
        q = self._queues.setdefault(agent_id, asyncio.Queue())
        try:
            return q.get_nowait()
        except asyncio.QueueEmpty:
            return None


# ── Demo Scenarios ────────────────────────────────────────────────


async def scenario_1_inline_completion(agent: CopilotAgent, bus: DemoBus) -> None:
    """Scenario 1: Human writes a function definition, copilot suggests body."""
    logger.info("═" * 60)
    logger.info("SCENARIO 1: Inline Completion")
    logger.info("═" * 60)
    logger.info("Human types: 'def calculate_exergy(system):'")

    # Build context as if captured from IDE
    payload = CopilotContextPayload(
        cursor=CursorContext(
            file_path="/project/engine.py",
            language="python",
            cursor_line=42,
            cursor_column=32,
            prefix="def calculate_exergy(system):",
            suffix="\n\ndef main():\n    pass\n",
        ),
        project=ProjectContext(
            open_files=["/project/engine.py", "/project/models.py"],
            codebase_symbols=["System", "ExergyResult", "ThermodynamicState"],
        ),
        trigger="keystroke",
        max_suggestions=3,
    )

    # Send context to copilot
    msg = new_message(
        sender="ide-demo",
        recipient=agent.agent_id,
        kind=MessageKind.TASK_REQUEST,
        payload=payload.model_dump(mode="json"),
    )
    await agent.handle_message(msg)

    # Read the response
    bus.log[-1]
    reply = await bus.receive("ide-demo")

    if reply and "suggestions" in reply.payload:
        batch = reply.payload
        logger.info("Copilot returned %d suggestions:", len(batch["suggestions"]))
        for i, s in enumerate(batch["suggestions"]):
            logger.info(
                "  [%d] %s (confidence=%s): %s",
                i + 1,
                s["kind"],
                s["confidence"],
                repr(s.get("inline_text", s.get("explanation", "")))[:80],
            )
            logger.info("      Explanation: %s", s["explanation"])

        # Human accepts the first suggestion
        if batch["suggestions"]:
            first = batch["suggestions"][0]
            logger.info("")
            logger.info("➤ Human ACCEPTS suggestion: %s", first["suggestion_id"])

            verdict_msg = new_message(
                sender="ide-demo",
                recipient=agent.agent_id,
                kind=MessageKind.TASK_RESULT,
                payload=SuggestionVerdict(
                    suggestion_id=first["suggestion_id"],
                    verdict=SuggestionStatus.ACCEPTED,
                    verdict_latency_ms=1200.0,
                ).model_dump(mode="json"),
            )
            await agent.handle_message(verdict_msg)
    else:
        logger.warning("No suggestions received")


async def scenario_2_diagnostic_fix(agent: CopilotAgent, bus: DemoBus) -> None:
    """Scenario 2: IDE reports a lint error, copilot suggests a fix."""
    logger.info("")
    logger.info("═" * 60)
    logger.info("SCENARIO 2: Diagnostic Fix")
    logger.info("═" * 60)
    logger.info("IDE reports: TypeError on line 15")

    payload = CopilotContextPayload(
        cursor=CursorContext(
            file_path="/project/utils.py",
            language="python",
            cursor_line=15,
            cursor_column=1,
            prefix='result = compute_hash(data, algorithm="sha256")',
            suffix="\nreturn result\n",
        ),
        project=ProjectContext(
            diagnostics=[
                {
                    "file": "/project/utils.py",
                    "line": 15,
                    "severity": "error",
                    "message": "TypeError: compute_hash() got unexpected keyword argument 'algorithm'",
                },
            ],
        ),
        trigger="diagnostic",
        max_suggestions=3,
    )

    msg = new_message(
        sender="ide-demo",
        recipient=agent.agent_id,
        kind=MessageKind.TASK_REQUEST,
        payload=payload.model_dump(mode="json"),
    )
    await agent.handle_message(msg)

    reply = await bus.receive("ide-demo")
    if reply and "suggestions" in reply.payload:
        batch = reply.payload
        for i, s in enumerate(batch["suggestions"]):
            logger.info(
                "  [%d] %s: %s",
                i + 1,
                s["kind"],
                s["explanation"],
            )
            if s.get("edits"):
                for edit in s["edits"]:
                    logger.info(
                        "      Edit: %s L%d → '%s'",
                        edit["file_path"],
                        edit["start_line"],
                        edit["replacement_text"][:60],
                    )

        # Human rejects this fix
        if batch["suggestions"]:
            first = batch["suggestions"][0]
            logger.info("")
            logger.info("➤ Human REJECTS suggestion: %s", first["suggestion_id"])

            verdict_msg = new_message(
                sender="ide-demo",
                recipient=agent.agent_id,
                kind=MessageKind.TASK_RESULT,
                payload=SuggestionVerdict(
                    suggestion_id=first["suggestion_id"],
                    verdict=SuggestionStatus.REJECTED,
                    feedback="I need to rename the parameter, not remove it",
                    verdict_latency_ms=3500.0,
                ).model_dump(mode="json"),
            )
            await agent.handle_message(verdict_msg)


async def scenario_3_multi_file_refactor(agent: CopilotAgent, bus: DemoBus) -> None:
    """Scenario 3: Human renames a symbol, copilot suggests propagation."""
    logger.info("")
    logger.info("═" * 60)
    logger.info("SCENARIO 3: Multi-File Refactor")
    logger.info("═" * 60)
    logger.info("Human renames 'compute_hash' → 'calculate_hash' in main.py")

    payload = CopilotContextPayload(
        cursor=CursorContext(
            file_path="/project/main.py",
            language="python",
            cursor_line=10,
            cursor_column=1,
            prefix="",
            suffix="",
        ),
        project=ProjectContext(
            recent_edits=[
                {
                    "file": "/project/main.py",
                    "line": 10,
                    "old": "compute_hash",
                    "new": "calculate_hash",
                },
            ],
            open_files=[
                "/project/main.py",
                "/project/utils.py",
                "/project/tests/test_hash.py",
            ],
        ),
        trigger="explicit",
        max_suggestions=3,
    )

    msg = new_message(
        sender="ide-demo",
        recipient=agent.agent_id,
        kind=MessageKind.TASK_REQUEST,
        payload=payload.model_dump(mode="json"),
    )
    await agent.handle_message(msg)

    reply = await bus.receive("ide-demo")
    if reply and "suggestions" in reply.payload:
        batch = reply.payload
        for i, s in enumerate(batch["suggestions"]):
            logger.info("  [%d] %s: %s", i + 1, s["kind"], s["explanation"])
            for edit in s.get("edits", []):
                logger.info(
                    "      %s: '%s' → '%s'",
                    edit["file_path"],
                    edit["original_text"],
                    edit["replacement_text"],
                )

        # Human partially accepts (only utils.py, not tests)
        if batch["suggestions"]:
            first = batch["suggestions"][0]
            logger.info("")
            logger.info("➤ Human PARTIALLY ACCEPTS: %s", first["suggestion_id"])

            verdict_msg = new_message(
                sender="ide-demo",
                recipient=agent.agent_id,
                kind=MessageKind.TASK_RESULT,
                payload=SuggestionVerdict(
                    suggestion_id=first["suggestion_id"],
                    verdict=SuggestionStatus.PARTIALLY_ACCEPTED,
                    human_modifications="Applied only to utils.py, skipped tests",
                    verdict_latency_ms=5200.0,
                ).model_dump(mode="json"),
            )
            await agent.handle_message(verdict_msg)


# ── Main ──────────────────────────────────────────────────────────


async def main() -> None:
    """Run the full copilot demo."""
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  CORTEX Level 3 Copilot - Integration Demo             ║")
    logger.info("║  Reality Level: C5-REAL                                 ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("")

    bus = DemoBus()
    agent = create_copilot_agent(bus, agent_id="copilot-demo")

    # Run all scenarios
    await scenario_1_inline_completion(agent, bus)
    await scenario_2_diagnostic_fix(agent, bus)
    await scenario_3_multi_file_refactor(agent, bus)

    # Final telemetry report
    telemetry = agent.get_telemetry()
    logger.info("")
    logger.info("═" * 60)
    logger.info("TELEMETRY REPORT")
    logger.info("═" * 60)
    logger.info("  Total suggestions:    %d", telemetry["total_suggestions"])
    logger.info("  Accepted:             %d", telemetry["total_accepted"])
    logger.info("  Rejected:             %d", telemetry["total_rejected"])
    logger.info("  Partially accepted:   %d", telemetry["total_partial"])
    logger.info("  Expired:              %d", telemetry["total_expired"])
    logger.info("  Acceptance rate:       %.1f%%", telemetry["acceptance_rate"] * 100)
    logger.info("  Pending verdicts:     %d", agent.get_pending_count())
    logger.info("")
    logger.info("✓ Demo complete. The copilot never acted alone.")


if __name__ == "__main__":
    asyncio.run(main())
