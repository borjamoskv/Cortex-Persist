"""
CORTEX Red Team — Parallel Adversarial Logic (Ω-Swarm-100).

This module implements the Parallel Red Team Agent, capable of spawning
100 parallel attack vectors to stress-test generated code (Ω-Siege).
Inspired by Devin and Manus architectures.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cortex.engine.isolation import IsolationManager
from cortex.engine.legion_vectors import RED_TEAM_SWARM, AttackVector
from cortex.engine.signals import log_limbic, log_motor

logger = logging.getLogger("cortex.engine.legion")

__all__ = ["BlueTeamAgent", "RedTeamSwarm", "LegionOmegaEngine", "SiegeResult", "LEGION_OMEGA"]


@dataclass
class SiegeResult:
    """Result of an adversarial forge cycle."""

    success: bool
    final_code: str
    cycles: int
    vulnerabilities: list[str] | None = None


class BlueTeamAgent:
    """Synthesis agent responsible for generating code under siege."""

    async def synthesize(self, intent: str, context: Mapping[str, Any], feedback: list[str]) -> str:
        """Generate code based on intent and adversarial feedback."""
        # Simulated LLM synthesis — incorporates feedback to evolve code between cycles.
        # In production, this calls a high-exergy frontier model (Ω₇)
        feedback_hash = hash(tuple(feedback)) if feedback else 0
        feedback_summary = "; ".join(feedback[:5]) if feedback else "none"
        return (
            f"# Implementation of {intent}\n"
            f"# Context: {context}\n"
            f"# Feedback ({len(feedback)}): {feedback_summary}\n"
            f"# Revision: {feedback_hash}\n"
        )


class RedTeamSwarm:
    """Orchestrator for 100 parallel attack vectors."""

    def __init__(
        self,
        replica_count: int = 100,
        vectors: list[AttackVector] | None = None,
        isolation: IsolationManager | None = None,
    ):
        self.replica_count = replica_count
        self.vectors = vectors or list(RED_TEAM_SWARM.values())
        self.isolation = isolation

    async def siege(self, code: str, context: Mapping[str, Any]) -> list[str]:
        """Subject code to all attack vectors in parallel using a 100-agent swarm."""
        total_agents = len(self.vectors) * self.replica_count
        msg = f"⚔️ Iniciando asedio con enjambre de {total_agents} agentes..."
        log_limbic(msg, source="RED")

        static_vectors = [v for v in self.vectors if not getattr(v, "is_dynamic", False)]
        dynamic_vectors = [v for v in self.vectors if getattr(v, "is_dynamic", False)]

        tasks = []
        # Phase A: Massive Static Parallelism (100 replicas per vector)
        for _ in range(self.replica_count):
            for v in static_vectors:
                tasks.append(v.attack(code, context))

        # Phase B: Isolated Dynamic Execution (Scaled conservatively)
        if dynamic_vectors and self.isolation:
            # Scale dynamic attacks conservatively to avoid host exhaustion
            dynamic_replicas = min(self.replica_count, 3)
            for _ in range(dynamic_replicas):
                for v in dynamic_vectors:
                    tasks.append(self._run_dynamic_attack(v, code, context))

        results = await asyncio.gather(*tasks)

        # Flatten results
        all_findings = [finding for result in results for finding in result]
        return all_findings

    async def _run_dynamic_attack(
        self, vector: AttackVector, code: str, context: Mapping[str, Any]
    ) -> list[str]:
        """Execute a dynamic attack within a Byzantine Sandbox."""
        if not self.isolation:
            return []

        async with self.isolation.provision_sandbox(label=f"siege_{vector.name}") as sandbox:
            # Transfer code to sandbox
            await sandbox.write_file("siege_target.py", code)

            # Attack execution: Run code and observe
            # Note: The vector logic for dynamic hunters is mostly observational.
            # We run the target and the sandbox captures leaks/side-effects.
            output = await sandbox.execute_python("siege_target.py")

            findings = []
            if output:
                if vector.name == "leak_hunter" and output.stderr:
                    # Naive leak detection based on stderr/traceback for now
                    if "ResourceWarning" in output.stderr or "leaked" in output.stderr.lower():
                        findings.append(
                            f"LeakHunter: Resource leak detected: {output.stderr[:100]}"
                        )

                if vector.name == "side_effect_watcher":
                    # Check for unauthorized files (anything other than siege_target.py)
                    # This uses the sandbox's restricted fs visibility.
                    pass  # Sandbox logic handles filesystem restrictions natively

            # Add vector-specific attack logic if it has content beyond the stub
            vector_findings = await vector.attack(code, context)
            findings.extend(vector_findings)

            return findings


class LegionOmegaEngine:
    """⚖️ LEGION-OMEGA: The Sovereign Arbiter."""

    def __init__(
        self,
        max_cycles: int = 3,
        vectors: list[AttackVector] | Mapping[str, AttackVector] | None = None,
        isolation: IsolationManager | None = None,
    ):
        self.blue_team = BlueTeamAgent()
        self.isolation = isolation or IsolationManager()
        # Normalización de vectores: asegurar que sea una lista de objetos, no un dict
        _vectors = vectors or RED_TEAM_SWARM
        if isinstance(_vectors, Mapping):
            self.vectors_list = list(_vectors.values())
        else:
            self.vectors_list = list(_vectors)

        self.red_team = RedTeamSwarm(vectors=self.vectors_list, isolation=self.isolation)
        self.max_cycles = max_cycles

    async def forge(self, intent: str, context: Mapping[str, Any] | None = None) -> SiegeResult:
        """Forge code through the fire of the siege."""
        ctx = context or {}
        feedback: list[str] = []
        final_code = ""
        previous_code = ""
        vulnerabilities: list[str] = []
        previous_v_count = 1_000_000  # Initial high value for integer comparison

        log_motor(f"LEGION-OMEGA: Forjando '{intent}'", action="FORGE")

        for cycle in range(1, self.max_cycles + 1):
            # Blue Team Synthesis
            code = await self.blue_team.synthesize(intent, ctx, feedback)

            # ─── Thermal Stagnation Guard (Ω₂) ───
            if code == previous_code:
                log_motor(
                    "Thermal Equilibrium: Code identity reached. No further delta.", action="STABLE"
                )
                break

            # Red Team Siege
            vulnerabilities = await self.red_team.siege(code, ctx)
            v_count = len(vulnerabilities)

            if not vulnerabilities:
                log_motor(f"Inmunidad Química alcanzada en ciclo {cycle}", action="Ω₆")
                return SiegeResult(success=True, final_code=code, cycles=cycle)

            # Entropy Regression Check
            # Si el número de vulnerabilidades aumenta o se estanca...
            if v_count >= previous_v_count and cycle > 1:
                logger.warning(
                    "⚠️ [LEGION] Stagnation in cycle %d (%d vs %d). Breaking thermal loop.",
                    cycle,
                    v_count,
                    previous_v_count,
                )
                break

            # Update stats for next cycle
            logger.info("❌ [LEGION] Ciclo %d fallido. Vulnerabilidades: %d", cycle, v_count)
            feedback.extend(vulnerabilities)
            final_code = code  # Keep last attempt
            previous_code = code
            previous_v_count = v_count

            # Small delay to simulate evolutionary cooldown
            await asyncio.sleep(0.05)

        log_motor("Asedio finalizado. Código entregado con deudas.", action="YIELD")
        return SiegeResult(
            success=False,
            final_code=final_code,
            cycles=self.max_cycles,
            vulnerabilities=vulnerabilities,
        )


# Global singleton
LEGION_OMEGA = LegionOmegaEngine()
