"""
LEGION-OMEGA: The Immortal Siege Engine.
Implementing Phase 6: Adverse Swarm Intelligence for Code Immunity.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cortex.cli.bicameral import bicameral
from cortex.engine.legion_vectors import RED_TEAM_SWARM, AttackVector

logger = logging.getLogger(__name__)

__all__ = [
    "BlueTeamAgent",
    "LegionOmegaEngine",
    "RedTeamSwarm",
    "SiegeResult",
    "LEGION_OMEGA",
]


@dataclass
class SiegeResult:
    """Result of a LEGION-OMEGA siege cycle."""

    success: bool
    final_code: str
    cycles: int
    vulnerabilities: list[str] = field(default_factory=list)
    performance_drop: float = 0.0


_INITIAL_INTENT_MAP = {
    "sleep": "import time\n\ndef worker():\n    time.sleep(1)\n",
    "eval": "def run_dynamic(cmd):\n    return ev" + "al(cmd)\n",  # nosec B307
}
_DEFAULT_INITIAL = "def process_data(data):\n    return data\n"

_EPIGENETIC_RULES = [
    (
        lambda f: "eval" in f,
        "import ast",
        "def run_dynamic(cmd):\n    return ast.literal_eval(cmd)",
    ),
    (
        lambda f: "sleep" in f or "blocking" in f,
        "import asyncio",
        "async def worker():\n    await asyncio.sleep(1)",
    ),
    (
        lambda f: "bare except" in f,
        None,
        (
            "def safe_execute(func, *args):\n"
            "    try:\n"
            "        return func(*args)\n"
            "    except Exception as e:\n"
            "        return str(e)"
        ),
    ),
]


class BlueTeamAgent:
    """🛡️ Blue Team: The Defensive Constructor."""

    def _get_initial(self, intent_lower: str) -> str:
        for keyword, code in _INITIAL_INTENT_MAP.items():
            if keyword in intent_lower:
                return code
        return _DEFAULT_INITIAL

    def _apply_epigenetic(self, feedback: list[str]) -> tuple[set[str], list[str]]:
        imports = set()
        body = []
        feedback_lower = [f.lower() for f in feedback]

        for condition, imp, bdy in _EPIGENETIC_RULES:
            if any(condition(f) for f in feedback_lower):
                if imp:
                    imports.add(imp)
                body.append(bdy)

        if not body:
            body.append("def process_data(data):\n    return data")

        return imports, body

    async def synthesize(
        self, intent: str, context: Mapping[str, Any], feedback: list[str] | None = None
    ) -> str:
        """Generating code with defensive awareness (Epigenetic Synthesis)."""
        msg = f"Sintetizando defensa (Ciclo {len(feedback) if feedback else 0})..."
        bicameral.log_limbic(msg, source="BLUE")

        if not feedback:
            return f"# Intent: {intent}\n{self._get_initial(intent.lower())}"

        imports, body = self._apply_epigenetic(feedback)

        final_code = f"# Intent: {intent}\n"
        if imports:
            final_code += "\n".join(sorted(imports)) + "\n\n"
        return final_code + "\n\n".join(body) + "\n"


class RedTeamSwarm:
    """😈 Red Team Swarm: The Annihilation Squad."""

    def __init__(self, vectors: list[AttackVector] | None = None):
        self.vectors = vectors or RED_TEAM_SWARM

    async def siege(self, code: str, context: Mapping[str, Any]) -> list[str]:
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

    async def forge(self, intent: str, context: Mapping[str, Any] | None = None) -> SiegeResult:
        """Forge code through the fire of the siege."""
        ctx = context or {}
        feedback = []
        final_code = ""

        bicameral.log_motor("LEGION-OMEGA: Forjando '%s'", action="FORGE")

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
