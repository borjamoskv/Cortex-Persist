#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
SOVEREIGN DECATHLON: The 10-Agent Full Spectrum Audit Swarm.
A coordinated siege of 10 specialized agents against CORTEX critical paths.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# ── SOVEREIGN PATH ANCHOR ──
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Standard Imports
from cortex.engine.legion_vectors import (
    AttackVector,
    ChronosSniper,
    EntropyDemon,
    EpistemicJustice,
    Intruder,
    LedgerPoisoner,
    OOMKiller,
    SiegeVector,
    VaultCracker,
)
from cortex.engine.squadrons import GhostHuntAgent, IntegrityAgent, KineticAgent
from cortex.engine.swarm import AsyncSignalBus, Squadron, SwarmAgent, SwarmSignal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("decathlon")


class DecathlonAgentAdapter(SwarmAgent):
    """Unified wrapper for Vector-based and SwarmAgent-based specialists."""

    def __init__(self, agent_id: str, bus: AsyncSignalBus, name: str, specialist: Any, engine: Any = None):
        super().__init__(agent_id, bus, engine)
        self.specialist_name = name
        self.specialist = specialist

    async def execute(self, target: str) -> SwarmSignal:
        """Execute the target using the underlying specialist strategy."""
        # Clean target string (remove earmarked suffix if present)
        clean_target = target.split("|")[0]

        # Read the target file content if it's a path
        content = ""
        target_path = Path(clean_target)
        try:
            if target_path.exists() and target_path.is_file():
                content = target_path.read_text(encoding="utf-8")
            else:
                content = clean_target  # Fallback to target string literal
        except Exception:  # noqa: BLE001
            content = clean_target

        findings = []
        context = {"intent": "audit", "agent_id": self.specialist_name}

        try:
            # 1. Adapt AttackVector interface: async attack(code, context)
            if isinstance(self.specialist, AttackVector):
                findings = await self.specialist.attack(content, context)
            # 2. Adapt SiegeVector interface: async attack(system, context)
            elif isinstance(self.specialist, SiegeVector):
                findings = await self.specialist.attack(self.engine, context)
            # 3. Adapt SwarmAgent execute(target) directly
            elif hasattr(self.specialist, "execute"):
                # Forward to the internal agent
                inner_signal = await self.specialist.execute(clean_target)
                # Re-wrap for the Decathlon report consistency
                return SwarmSignal(
                    agent_id=self.specialist_name.upper(),
                    target=clean_target,
                    status=inner_signal.status,
                    payload=inner_signal.payload,
                    metrics=inner_signal.metrics
                )
            else:
                findings = [f"Unsupported specialist type: {type(self.specialist)}"]
        except Exception as e:  # noqa: BLE001
            logger.error("Specialist [%s] crashed: %s", self.specialist_name, e)
            findings = [f"Critical analysis failure: {e}"]

        status = "SUCCESS" if findings else "VOID"
        return SwarmSignal(
            agent_id=self.specialist_name.upper(),
            target=clean_target,
            status=status,
            payload={"findings": findings},
            metrics={"found_count": len(findings)}
        )


class DecathlonSquadron(Squadron):
    """The Sovereign 10 Squadron: Strictly One of Each Specialist."""

    SQUAD_NAME = "SOVEREIGN_10"
    REPLICAS = 10

    def __init__(self, engine: Any = None):
        super().__init__(engine)
        # Initialize internal specialists
        self.specialists = [
            ("intruder", Intruder()),
            ("oom_killer", OOMKiller()),
            ("entropy_demon", EntropyDemon()),
            ("chronos_sniper", ChronosSniper()),
            ("ledger_poisoner", LedgerPoisoner()),
            ("vault_cracker", VaultCracker()),
            ("epistemic_justice", EpistemicJustice()),
            ("integrity_linter", IntegrityAgent("linter", self.bus, engine)),
            ("kinetic_api", KineticAgent("api_engager", self.bus, engine)),
            ("ghost_hunter", GhostHuntAgent("ghost_hunter", self.bus, engine))
        ]

    def _create_agent(self, agent_id: str) -> SwarmAgent:
        # This method is used by deploy() to spawn the 10 agents
        idx = int(agent_id.split("-")[-1])
        name, spec = self.specialists[idx]
        return DecathlonAgentAdapter(agent_id, self.bus, name, spec, self.engine)

    async def deploy(self, target_pattern: str | None = None) -> dict[str, Any]:
        """Override deploy to ensure strict 1-to-1 agent-target mapping."""
        logger.info("🚀 [SOVEREIGN-10] Coordinating 10 specialized audits...")

        # 1. Spawn Agents
        self.agents = [
            self._create_agent(f"{self.SQUAD_NAME}-{i:03d}") for i in range(self.REPLICAS)
        ]

        # 2. Assign exactly ONE task to each agent and run in parallel
        # We don't use the shared queue here to prevent race conditions.
        tasks = []
        for agent in self.agents:
            # Each agent gets the same target pattern
            # Using a single-item queue for the base SwarmAgent.run compatibility
            q: asyncio.Queue[str] = asyncio.Queue()
            q.put_nowait(target_pattern or "N/A")
            tasks.append(asyncio.create_task(agent.run(q)))

        await asyncio.gather(*tasks)

        # 3. CRYSTALLIZE
        signals = await self.bus.get_all()
        return await self._crystallize(signals)

    async def _crystallize(self, signals: list[SwarmSignal]) -> dict[str, Any]:
        """Crystallize findings with Sovereign Aesthetic."""
        report = await super()._crystallize(signals)
        
        print("\n" + "=" * 80)
        target_name = report["raw"][0]["target"] if report["raw"] else "N/A"
        print(f"💎 SOVEREIGN DECATHLON REPORT: {target_name}")
        print("=" * 80)

        # Sort signals alphabetically by agent_id for a clean report
        sorted_signals = sorted(signals, key=lambda x: x.agent_id)

        for s in sorted_signals:
            agent_label = s.agent_id.ljust(20)
            status_emoji = "✅" if s.status == "VOID" else "❌" if s.status == "FAILURE" else "🔍"
            findings = s.payload.get("findings", [])
            findings_count = s.payload.get("found_count", len(findings))
            
            # Special handling for SwarmAgent results (legacy payload)
            if not findings and "lint_warnings" in s.payload:
                findings_count = s.payload["lint_warnings"] + s.payload["type_errors"]
                status_emoji = "🛡️"
            elif not findings and "loc_drop" in s.payload:
                findings_count = s.payload.get("loc_drop", 0)
                status_emoji = "👻"
            elif not findings and "yield_value" in s.payload:
                findings_count = s.payload.get("yield_value", 0)
                status_emoji = "💸"

            print(f"{status_emoji} [{agent_label}] Impact: {findings_count}")
            for f in findings:
                print(f"    ↳ {f}")
        
        print("=" * 80 + "\n")
        return report

    async def _crystallize(self, signals: list[SwarmSignal]) -> dict[str, Any]:
        """Crystallize findings with Sovereign Aesthetic."""
        report = await super()._crystallize(signals)
        
        print("\n" + "=" * 80)
        print("💎 SOVEREIGN DECATHLON REPORT: " + (report["raw"][0]["target"] if report["raw"] else "N/A"))
        print("=" * 80)

        # Sort signals to keep report consistent
        sorted_signals = sorted(signals, key=lambda x: x.agent_id)

        for s in sorted_signals:
            agent_label = s.agent_id.ljust(20)
            status_emoji = "✅" if s.status == "VOID" else "❌" if s.status == "FAILURE" else "🔍"
            findings = s.payload.get("findings", [])
            findings_count = s.payload.get("found_count", len(findings))
            
            # Special handling for SwarmAgent results (legacy payload)
            if not findings and "lint_warnings" in s.payload:
                findings_count = s.payload["lint_warnings"] + s.payload["type_errors"]
                status_emoji = "🛡️"
            elif not findings and "loc_drop" in s.payload:
                findings_count = s.payload.get("loc_drop", 0)
                status_emoji = "👻"
            elif not findings and "yield_value" in s.payload:
                findings_count = s.payload.get("yield_value", 0)
                status_emoji = "💸"

            print(f"{status_emoji} [{agent_label}] Impact: {findings_count}")
            for f in findings:
                print(f"    ↳ {f}")
        
        print("=" * 80 + "\n")
        return report


async def main():
    # Attempt to initialize engine if env permits
    from cortex.engine import CortexEngine
    engine = CortexEngine(":memory:", auto_embed=False)
    await engine.init_db()

    target = sys.argv[1] if len(sys.argv) > 1 else "cortex/engine/ledger.py"
    
    decathlon = DecathlonSquadron(engine=engine)
    _ = await decathlon.deploy(target)
    
    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
