"""
LEGION-OMEGA: The Immortal Siege Engine.
Implementing Phase 6: Adverse Swarm Intelligence for Code Immunity.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from cortex.cli.bicameral import bicameral
from cortex.engine.legion_vectors import RED_TEAM_SWARM, AttackVector

logger = logging.getLogger(__name__)


@dataclass
class SiegeResult:
    """Result of a LEGION-OMEGA siege cycle."""

    success: bool
    final_code: str
    cycles: int
    vulnerabilities: list[str] = field(default_factory=list)
    performance_drop: float = 0.0


class BlueTeamAgent:
    """🛡️ Blue Team: The Defensive Constructor."""

    async def synthesize(
        self, intent: str, context: dict[str, Any], feedback: list[str] = None  # type: ignore[reportArgumentType]
    ) -> str:
        """Generating code with defensive awareness (Epigenetic Synthesis)."""
        msg = f"Sintetizando defensa (Ciclo {len(feedback) if feedback else 0})..."
        bicameral.log_limbic(msg, source="BLUE")

        # Base code
        code = f"# Intent: {intent}\n"

        if not feedback:
            # Initial generation
            if "sleep" in intent.lower():
                code += "import time\n\ndef worker():\n    time.sleep(1)\n"
            elif "eval" in intent.lower():
                code += "def run_dynamic(cmd):\n    return eval(cmd)\n"
            else:
                code += "def process_data(data):\n    return data\n"
            return code

        # Epigenetic Transformation: Actual morphing based on feedback
        imports = set()
        body = []

        if any("eval" in f.lower() for f in feedback):
            imports.add("import ast")
            body.append("def run_dynamic(cmd):\n    return ast.literal_eval(cmd)")

        if any("sleep" in f.lower() or "blocking" in f.lower() for f in feedback):
            imports.add("import asyncio")
            body.append("async def worker():\n    await asyncio.sleep(1)")

        if any("bare except" in f.lower() for f in feedback):
            body.append(
                "def safe_execute(func, *args):\n    try:\n        return func(*args)\n    except Exception as e:\n        return str(e)"
            )

        if not body:
            body.append("def process_data(data):\n    return data")

        final_code = f"# Intent: {intent}\n"
        if imports:
            final_code += "\n".join(sorted(list(imports))) + "\n\n"
        final_code += "\n\n".join(body) + "\n"

        return final_code


class RedTeamSwarm:
    """😈 Red Team Swarm: The Annihilation Squad."""

    def __init__(self, vectors: list[AttackVector] = None):  # type: ignore[reportArgumentType]
        self.vectors = vectors or RED_TEAM_SWARM

    async def siege(self, code: str, context: dict[str, Any]) -> list[str]:
        """Subject code to all attack vectors in parallel."""
        bicameral.log_limbic("⚔️ Iniciando asedio de enjambre...", source="RED")
        tasks = [v.attack(code, context) for v in self.vectors]
        results = await asyncio.gather(*tasks)

        # Flatten results
        all_findings = [finding for result in results for finding in result]
        return all_findings


class LegionOmegaEngine:
    """⚖️ LEGION-OMEGA: The Sovereign Arbiter."""

    def __init__(self, max_cycles: int = 3):
        self.blue_team = BlueTeamAgent()
        self.red_team = RedTeamSwarm()
        self.max_cycles = max_cycles

    async def forge(self, intent: str, context: dict[str, Any] = None) -> SiegeResult:  # type: ignore[reportArgumentType]
        """Forge code through the fire of the siege."""
        ctx = context or {}
        feedback = []
        final_code = ""

        bicameral.log_motor(f"LEGION-OMEGA: Forjando '{intent}'", action="FORGE")

        for cycle in range(1, self.max_cycles + 1):
            # Blue Team Synthesis
            code = await self.blue_team.synthesize(intent, ctx, feedback)

            # Red Team Siege
            vulnerabilities = await self.red_team.siege(code, ctx)

            if not vulnerabilities:
                bicameral.log_motor(f"Inmunidad Química alcanzada en ciclo {cycle}", action="Ω₆")
                return SiegeResult(success=True, final_code=code, cycles=cycle)

            # Report failure and collect feedback for next cycle
            logger.warning(
                "❌ [LEGION] Ciclo %d fallido. Vulnerabilidades: %s", cycle, vulnerabilities
            )
            feedback.extend(vulnerabilities)
            final_code = code  # Keep last attempt

            # Small delay to simulate evolutionary cooldown
            await asyncio.sleep(0.1)

        bicameral.log_motor("Asedio fallido tras ciclos máximos. Código frágil.", action="FAIL")
        return SiegeResult(
            success=False, final_code=final_code, cycles=self.max_cycles, vulnerabilities=feedback
        )


# Global singleton
LEGION_OMEGA = LegionOmegaEngine()
