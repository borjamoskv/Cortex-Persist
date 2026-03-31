#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
SOVEREIGN 25 (SILVER SWARM): Full Spectrum 25-Agent Audit.
A coordinated parallel siege of 25 specialized agents against CORTEX-Persist core.
"""

import asyncio
import logging
import sys
from collections.abc import Mapping
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
logger = logging.getLogger("silver_swarm")

# ── NEW SPECIALIZED AGENTS (11-25) ──

class DeadlockDemon:
    """Vector: Concurrency & Lock-Ordering (The Deadlock Demon)."""
    name = "deadlock_demon"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if ".acquire(" in code and ".release(" not in code:
            if "async with" not in code:  # async with handles release automatically
                findings.append("Potential Deadlock: Lock acquired without manual release.")
        
        # Hardened Check: Only flag identical nested locks if possible, 
        # or flag >2 levels of nesting as a smells.
        if code.count("async with") > 2:
            findings.append("Deep Nesting: Risk of complex resource contention.")
        return findings

class DiskDriller:
    """Vector: IO Bottlenecks (The Disk Driller)."""
    name = "disk_driller"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "open(" in code and ".read()" in code.split("open(")[1]:
            if "with " not in code:
                findings.append("IO Risk: File opened without context manager.")
        if ".write(" in code and "loop" in str(context).lower():
            findings.append("IO Bottleneck: Synchronous write in possible loop.")
        return findings

class ShadowHunter:
    """Vector: Supply Chain & Path Mutation (The Shadow Hunter)."""
    name = "shadow_hunter"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        dangerous = ["sys.path.append(", "sys.path.insert(", "PYTHONPATH"]
        for d in dangerous:
            if d in code:
                findings.append(f"Path Mutation: Dangerous `{d}` detected. Potential shadowing.")
        return findings

class LeakLord:
    """Vector: Memory Leaks & Unbounded Caches (The Leak Lord)."""
    name = "leak_lord"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if " = {}" in code or " = []" in code:
            if "__init__" not in code and "global" in code:
                findings.append("Memory Risk: Global collection without clear eviction policy.")
        if "lru_cache(maxsize=None)" in code:
            findings.append("Unbounded Cache: Memory leak risk via `maxsize=None`.")
        return findings

class TypeTemplar:
    """Vector: Type Safety & Integrity (The Type Templar)."""
    name = "type_templar"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "Callable = " in code and "Any" in code:
            findings.append("Type Dilution: Use of `Any` in critical Callable definition.")
        if "type: ignore" in code:
            findings.append("Type Evasion: Explicit `type: ignore` found.")
        return findings

class DocDoctor:
    """Vector: Documentation & Implementation Mismatch (The Doc Doctor)."""
    name = "doc_doctor"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if '"""' in code and "Args:" not in code:
            findings.append("Documentation Debt: Docstring found but missing structured Args.")
        return findings

class LogicLoom:
    """Vector: Logic Redundancy & Boolean Collapse (The Logic Loom)."""
    name = "logic_loom"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "if" in code and "==" in code and "True" in code:
            findings.append("Logic Debt: Redundant `if X == True` detected.")
        return findings

class NoirKnight:
    """Vector: Aesthetic & Noir Naming (The Noir Knight)."""
    name = "noir_knight"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "color" in code and "#0A0A0A" not in code and "#000000" not in code:
             # Just a joke/test for Industrial Noir
             pass
        return findings

class TokenTailor:
    """Vector: Computational Capital & Efficiency (The Token Tailor)."""
    name = "token_tailor"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "while True:" in code and "asyncio.sleep" not in code:
            findings.append("Exergy Loss: Tight loop without yield point (Token consumption spike).")
        return findings

class OwaspOracle:
    """Vector: Security Standards (The OWASP Oracle)."""
    name = "owasp_oracle"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "f\"SELECT" in code or "f'SELECT" in code:
            findings.append("A1-Injection: Potential SQL string interpolation.")
        return findings

class ContractCracker:
    """Vector: API & Contract Mismatch (The Contract Cracker)."""
    name = "contract_cracker"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "TypedDict" in code and "total=False" in code:
            findings.append("Contract Risk: Non-total TypedDict may cause runtime attribute errors.")
        return findings

class SeedSower:
    """Vector: Determinism & Entropy Zero (The Seed Sower)."""
    name = "seed_sower"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "random." in code and "random.seed" not in code:
            findings.append("Entropy Risk: Non-deterministic random usage without explicit seed.")
        return findings

class StarvationSniper:
    """Vector: Event Loop Starvation (The Starvation Sniper)."""
    name = "starvation_sniper"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "async def" in code and "import time" in code and "time.sleep" in code:
            findings.append("Loop Starvation: `time.sleep` in async context detected.")
        return findings

class VecVulture:
    """Vector: Vector Search & Indexing (The Vec Vulture)."""
    name = "vec_vulture"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "USING vec0" in code and "NOT EXISTS" not in code:
            findings.append("Indexing Risk: `vec0` table creation without safety check.")
        return findings

class MetaMaster:
    """Vector: Metadata & Ledger Consistency (The Meta Master)."""
    name = "meta_master"
    async def attack(self, code: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        if "cortex_meta" in code and "INSERT" in code and "ON CONFLICT" not in code:
            findings.append("Metadata Risk: Key insertion without conflict resolution.")
        return findings

# ── ORCHESTRATION ──

class SilverAgentAdapter(SwarmAgent):
    """Unified wrapper for 25 specialists."""
    def __init__(self, agent_id: str, bus: AsyncSignalBus, name: str, specialist: Any, engine: Any = None):
        super().__init__(agent_id, bus, engine)
        self.specialist_name = name
        self.specialist = specialist

    async def execute(self, target: str) -> SwarmSignal:
        content = ""
        target_path = Path(target)
        try:
            if target_path.exists() and target_path.is_file():
                content = target_path.read_text(encoding="utf-8")
            else:
                content = target
        except Exception:
            content = target

        findings = []
        context = {"intent": "audit", "agent_id": self.specialist_name}
        try:
            if isinstance(self.specialist, AttackVector):
                findings = await self.specialist.attack(content, context)
            elif isinstance(self.specialist, SiegeVector):
                findings = await self.specialist.attack(self.engine, context)
            elif hasattr(self.specialist, "execute"):
                inner_signal = await self.specialist.execute(target)
                return SwarmSignal(
                    agent_id=self.specialist_name.upper(),
                    target=target,
                    status=inner_signal.status,
                    payload=inner_signal.payload,
                    metrics=inner_signal.metrics,
                )
            else:
                findings = [f"Unsupported specialist: {type(self.specialist)}"]
        except Exception as e:
            logger.error("Agent [%s] crash: %s", self.specialist_name, e)
            findings = [f"Failure: {e}"]

        return SwarmSignal(agent_id=self.specialist_name.upper(), target=target,
                           status="SUCCESS" if findings else "VOID", payload={"findings": findings},
                           metrics={"found_count": len(findings)})

class SilverSquadron(Squadron):
    """The Sovereign 25: Silver Swarm Orchestrator."""
    SQUAD_NAME = "SILVER_25"
    REPLICAS = 25

    def __init__(self, engine: Any = None):
        super().__init__(engine)
        self.specialists = [
            ("intruder", Intruder()), ("oom_killer", OOMKiller()), ("entropy_demon", EntropyDemon()),
            ("chronos_sniper", ChronosSniper()), ("ledger_poisoner", LedgerPoisoner()),
            ("vault_cracker", VaultCracker()), ("epistemic_justice", EpistemicJustice()),
            ("integrity_linter", IntegrityAgent("linter", self.bus, engine)),
            ("kinetic_api", KineticAgent("api_engager", self.bus, engine)),
            ("ghost_hunter", GhostHuntAgent("ghost_hunter", self.bus, engine)),
            ("deadlock_demon", DeadlockDemon()), ("disk_driller", DiskDriller()),
            ("shadow_hunter", ShadowHunter()), ("leak_lord", LeakLord()),
            ("type_templar", TypeTemplar()), ("doc_doctor", DocDoctor()),
            ("logic_loom", LogicLoom()), ("noir_knight", NoirKnight()),
            ("token_tailor", TokenTailor()), ("owasp_oracle", OwaspOracle()),
            ("contract_cracker", ContractCracker()), ("seed_sower", SeedSower()),
            ("starvation_sniper", StarvationSniper()), ("vec_vulture", VecVulture()),
            ("meta_master", MetaMaster())
        ]

    def _create_agent(self, agent_id: str) -> SwarmAgent:
        idx = int(agent_id.split("-")[-1])
        name, spec = self.specialists[idx]
        return SilverAgentAdapter(agent_id, self.bus, name, spec, self.engine)

    async def deploy(self, target: str | None = None) -> dict[str, Any]:
        logger.info("🚀 [SILVER-25] Deploying 25 specialized agents...")
        self.agents = [self._create_agent(f"{self.SQUAD_NAME}-{i:03d}") for i in range(self.REPLICAS)]
        tasks = []
        for agent in self.agents:
            q: asyncio.Queue[str] = asyncio.Queue()
            q.put_nowait(target or "N/A")
            tasks.append(asyncio.create_task(agent.run(q)))
        await asyncio.gather(*tasks)
        signals = await self.bus.get_all()
        return await self._crystallize(signals)

    async def _crystallize(self, signals: list[SwarmSignal]) -> dict[str, Any]:
        report = await super()._crystallize(signals)
        print("\n" + "="*80 + "\n💎 SOVEREIGN 25 (SILVER SWARM) REPORT\n" + "="*80)
        for s in sorted(signals, key=lambda x: x.agent_id):
            emoji = "✅" if s.status == "VOID" else "❌" if s.status == "FAILURE" else "🔍"
            print(f"{emoji} [{s.agent_id.ljust(20)}] Found: {s.payload.get('findings', []) or 0}")
        print("="*80 + "\n")
        return report

async def main():
    from cortex.engine import CortexEngine
    engine = CortexEngine(":memory:", auto_embed=False)
    await engine.init_db()
    target = sys.argv[1] if len(sys.argv) > 1 else "cortex/engine/ledger.py"
    silver = SilverSquadron(engine=engine)
    await silver.deploy(target)
    await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
