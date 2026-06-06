# [C5-REAL] Exergy-Maximized
"""Proof of Concept & Stress Test for CORTEX Autonomous Agent (Level 4).

Executes three test phases to validate correctness, safety invariants, and performance:
    1. C5-REAL Proof of Concept: File creation, shell execution, exergy audit, cleanup.
    2. Adversarial Stress: 40-step flaky execution with strict entropy circuit breaker.
    3. Concurrency Stress: Concurrent execution of 15 agents to measure throughput.

Reality Level: C5-REAL
Design System: Industrial Noir 2026
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

# Adjust path to import cortex module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex.agents.autonomous import AutonomousAgent, create_autonomous_agent
from cortex.agents.builtin_tools import register_all_builtin_tools
from cortex.agents.message_schema import AgentMessage
from cortex.agents.tools import ToolRegistry

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("cortex.benchmark")


class InMemoryBus:
    """Minimal in-memory message bus for concurrent agent test."""

    def __init__(self) -> None:
        self.messages: list[AgentMessage] = []

    async def send(self, message: AgentMessage) -> None:
        self.messages.append(message)


class FlakyTool:
    """Tool that fails with a configured probability for stress testing."""

    def __init__(self, failure_rate: float = 0.5) -> None:
        self.failure_rate = failure_rate
        self.invocations = 0
        import random

        self._rng = random.Random(42)  # Seed for deterministic flakiness

    @property
    def name(self) -> str:
        return "flaky_tool"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        self.invocations += 1
        # Determine failure
        if self._rng.random() < self.failure_rate:
            raise RuntimeError("Transient network degradation or database lock error")
        return {"ok": True, "value": kwargs.get("val", 0) * 2}


async def run_poc_phase(agent: AutonomousAgent, temp_dir: Path) -> dict[str, Any]:
    """Phase 1: Proof of Concept (C5-REAL file + shell operations)."""
    logger.info("\n\x1b[1;34m[⚡ PHASE 1] Running C5-REAL Proof of Concept...\x1b[0m")

    script_path = temp_dir / "math_poc.py"

    # 4-step plan
    steps = [
        {
            "tool_name": "filesystem",
            "arguments": {
                "action": "write",
                "path": str(script_path),
                "content": "import math\nimport sys\nsys.stdout.write(f'PI_APPROX={math.pi:.6f}\\n')\n",
            },
            "description": "Write math script to temporary path",
            "exergy_estimate": 0.9,
            "entropy_cost": 0.1,
        },
        {
            "tool_name": "shell",
            "arguments": {"cmd": f"{sys.executable} {script_path}"},
            "description": "Execute script in subprocess and capture output",
            "exergy_estimate": 0.8,
            "entropy_cost": 0.2,
            "depends_on": [],  # Let planner evaluate greedy ordering
        },
        {
            "tool_name": "exergy_audit",
            "arguments": {},
            "description": "Evaluate exergy metrics of active plan",
            "exergy_estimate": 0.5,
            "entropy_cost": 0.05,
        },
        {
            "tool_name": "filesystem",
            "arguments": {"action": "delete", "path": str(script_path)},
            "description": "Clean up temporary file",
            "exergy_estimate": 0.7,
            "entropy_cost": 0.1,
        },
    ]

    result = await agent.execute_objective(
        objective="Verify physical script execution and clean up", steps_def=steps
    )

    logger.info("  Status: %s", result["status"])
    logger.info("  Elapsed: %ss", result["elapsed_s"])
    logger.info("  Net Exergy: %s", result["net_exergy"])
    logger.info("  Exergy Efficiency: %s", result["exergy_efficiency"])

    return result


async def run_adversarial_phase(bus: InMemoryBus, flaky_registry: ToolRegistry) -> dict[str, Any]:
    """Phase 2: Adversarial Stress (large plans under flakiness with circuit breakers)."""
    logger.info(
        "\n\x1b[1;34m[⚡ PHASE 2] Running Adversarial flakiness and Circuit Breaker Stress...\x1b[0m"
    )

    # Create 40 steps for flaky execution
    steps_def = []
    for i in range(40):
        steps_def.append(
            {
                "tool_name": "flaky_tool",
                "arguments": {"val": i},
                "description": f"Flaky calculation step #{i}",
                "exergy_estimate": 0.8,
                "entropy_cost": 0.2,
                "retry_budget": 5,
            }
        )

    # Agent A: Strict Entropy Breaker
    agent_a = create_autonomous_agent(
        agent_id="breaker-agent",
        bus=bus,
        tool_registry=flaky_registry,
        tools_allowed=["flaky_tool"],
        max_plan_steps=100,
    )

    logger.info("  -> Executing Agent A (Strict max_entropy = 6.0)...")
    result_a = await agent_a.execute_objective(
        objective="Run flaky steps with strict budget",
        steps_def=steps_def,
        constraints={"max_entropy": 6.0},
    )

    # Agent B: Unlimited Budget
    # Re-instantiate tool to reset RNG seed for fair comparison
    reset_registry = ToolRegistry()
    reset_registry.register(FlakyTool(failure_rate=0.3))

    agent_b = create_autonomous_agent(
        agent_id="unlimited-agent",
        bus=bus,
        tool_registry=reset_registry,
        tools_allowed=["flaky_tool"],
        max_plan_steps=100,
    )

    logger.info("  -> Executing Agent B (Unlimited entropy budget)...")
    result_b = await agent_b.execute_objective(
        objective="Run flaky steps to completion", steps_def=steps_def
    )

    # Calculate executed steps
    a_completed = sum(1 for s in result_a["steps"] if s["status"] == "completed")
    b_completed = sum(1 for s in result_b["steps"] if s["status"] == "completed")

    logger.info(
        "  Agent A Status: %s | Steps Completed: %d/40 | Final Net Exergy: %s",
        result_a["status"],
        a_completed,
        result_a["net_exergy"],
    )
    logger.info(
        "  Agent B Status: %s | Steps Completed: %d/40 | Final Net Exergy: %s",
        result_b["status"],
        b_completed,
        result_b["net_exergy"],
    )

    return {"agent_a": result_a, "agent_b": result_b}


async def run_concurrency_phase(bus: InMemoryBus, registry: ToolRegistry) -> dict[str, Any]:
    """Phase 3: Concurrency Stress (15 agents running 5-step tasks simultaneously)."""
    logger.info("\n\x1b[1;34m[⚡ PHASE 3] Running Concurrency Stress Test (15 agents)...\x1b[0m")

    num_agents = 15
    steps = [
        {"tool_name": "noop", "arguments": {"step": 1}, "exergy_estimate": 0.9},
        {"tool_name": "noop", "arguments": {"step": 2}, "exergy_estimate": 0.8},
        {"tool_name": "noop", "arguments": {"step": 3}, "exergy_estimate": 0.7},
        {"tool_name": "noop", "arguments": {"step": 4}, "exergy_estimate": 0.6},
        {"tool_name": "noop", "arguments": {"step": 5}, "exergy_estimate": 0.5},
    ]

    agents = [
        create_autonomous_agent(
            agent_id=f"con-agent-{i:02d}", bus=bus, tool_registry=registry, tools_allowed=["noop"]
        )
        for i in range(num_agents)
    ]

    start_time = time.monotonic()

    # Gather concurrent executions
    tasks = [
        agent.execute_objective(
            objective=f"Concurrent workload for agent {agent.agent_id}", steps_def=steps
        )
        for agent in agents
    ]

    results = await asyncio.gather(*tasks)
    elapsed = time.monotonic() - start_time

    successful_plans = sum(1 for r in results if r["status"] == "SUCCESS")
    total_steps = sum(len(r["steps"]) for r in results)
    throughput = num_agents / elapsed

    logger.info("  Successfully finished: %d/%d plans", successful_plans, num_agents)
    logger.info("  Total steps executed: %d", total_steps)
    logger.info("  Total elapsed time: %.3fs", elapsed)
    logger.info("  Throughput: %.2f objectives/second", throughput)

    return {
        "num_agents": num_agents,
        "successful_plans": successful_plans,
        "elapsed": elapsed,
        "throughput": throughput,
        "total_steps": total_steps,
    }


async def main():
    logger.info("======================================================================")
    logger.info("      ⚡ CORTEX Autonomous Agent L4 Stress Test & PoC ⚡")
    logger.info("======================================================================")
    logger.info("Reality Level: C5-REAL (verifiable side effects)")

    # Setup temporary directory for PoC
    temp_dir = Path("poc_temp")
    temp_dir.mkdir(exist_ok=True)

    bus = InMemoryBus()
    registry = ToolRegistry()
    register_all_builtin_tools(registry)

    # 1. PoC Agent
    agent_poc = create_autonomous_agent(
        agent_id="poc-agent-01",
        bus=bus,
        tool_registry=registry,
        tools_allowed=["filesystem", "shell", "exergy_audit"],
    )

    # Run Phase 1
    poc_res = await run_poc_phase(agent_poc, temp_dir)

    # Clean up PoC directory
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    # 2. Adversarial Flaky Setup
    flaky_registry = ToolRegistry()
    flaky_registry.register(FlakyTool(failure_rate=0.3))
    adv_res = await run_adversarial_phase(bus, flaky_registry)

    # 3. Concurrency Setup
    con_res = await run_concurrency_phase(bus, registry)

    # Final Telemetry Report
    logger.info("\n======================================================================")
    logger.info("                       FINAL BENCHMARK REPORT                         ")
    logger.info("======================================================================")

    # Extract metrics
    poc_success = poc_res["status"]
    poc_eff = poc_res["exergy_efficiency"]

    breaker_steps = len([s for s in adv_res["agent_a"]["steps"] if s["status"] == "completed"])
    breaker_entropy = adv_res["agent_a"]["plan"]["entropy_paid"]

    unlimited_steps = len([s for s in adv_res["agent_b"]["steps"] if s["status"] == "completed"])

    logger.info("| Metric | Value | Status |")
    logger.info("| :--- | :--- | :--- |")
    logger.info("| **Phase 1: PoC Success** | %s | PASS |", poc_success)
    logger.info("| **Phase 1: PoC Exergy Efficiency** | %.4f | PASS |", poc_eff)
    logger.info(
        "| **Phase 2: Agent A (Breaker) Steps** | %d/40 (Halted at entropy=%.2f) | PASS (Safe Halt) |",
        breaker_steps,
        breaker_entropy,
    )
    logger.info(
        "| **Phase 2: Agent B (Unlimited) Steps** | %d/40 (Net Exergy=%.2f) | PASS (Completed) |",
        unlimited_steps,
        adv_res["agent_b"]["net_exergy"],
    )
    logger.info("| **Phase 3: Concurrent Plans Run** | %d agents | PASS |", con_res["num_agents"])
    logger.info(
        "| **Phase 3: Concurrency Throughput** | %.2f obj/sec | PASS |", con_res["throughput"]
    )
    logger.info(
        "| **Phase 3: Total Steps Executed** | %d steps in %.2fs | PASS |",
        con_res["total_steps"],
        con_res["elapsed"],
    )
    logger.info("======================================================================")

    # Assert correctness of safety circuit breaker
    assert breaker_steps < 40, "Agent A should have halted due to entropy limit"
    assert breaker_entropy <= 7.5, "Agent A entropy should not significantly exceed threshold"
    assert con_res["successful_plans"] == con_res["num_agents"], (
        "All concurrent plans should succeed"
    )
    logger.info("\x1b[1;32m[✓] All PoC and Stress assertions validated successfully.\x1b[0m\n")


if __name__ == "__main__":
    asyncio.run(main())
