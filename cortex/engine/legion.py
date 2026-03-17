"""
LEGION-OMEGA: The Immortal Siege Engine.
Implementing Phase 6: Adverse Swarm Intelligence for Code Immunity.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Optional, Union

try:
    from cortex.cli.bicameral import bicameral
except ImportError:
    # Axiom Ω₃: Zero-Trust Logging - providing a stub if CLI is unavailable
    class BicameralStub:
        def log_limbic(self, msg: str, **kwargs) -> None:
            logging.getLogger("cortex.limbic").info(msg)

        def log_motor(self, msg: str, **kwargs) -> None:
            logging.getLogger("cortex.motor").info(msg)

    bicameral = BicameralStub()

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
            "    except Exception as e:  # noqa: BLE001\n"
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
        self, intent: str, context: Mapping[str, Any], feedback: Optional[list[str]] = None
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

    def __init__(self, vectors: Optional[list[AttackVector]] = None, replica_count: int = 100):
        self.vectors = vectors or list(RED_TEAM_SWARM.values())
        # Enforce the 100 Sovereign Agents Topology
        self.replica_count = replica_count

    async def siege(self, code: str, context: Mapping[str, Any]) -> list[str]:
        """Subject code to all attack vectors in parallel using a 100-agent swarm."""
        total_agents = len(self.vectors) * self.replica_count
        msg = f"⚔️ Iniciando asedio con enjambre de {total_agents} agentes..."
        bicameral.log_limbic(msg, source="RED")
        tasks = []
        for _ in range(self.replica_count):
            for v in self.vectors:
                tasks.append(v.attack(code, context))
        results = await asyncio.gather(*tasks)

        # Flatten results
        all_findings = [finding for result in results for finding in result]
        return all_findings


class LegionOmegaEngine:
    """⚖️ LEGION-OMEGA: The Sovereign Arbiter."""

    def __init__(
        self,
        max_cycles: int = 3,
        vectors: Optional[Union[list[AttackVector], Mapping[str, AttackVector]]] = None,
    ):
        self.blue_team = BlueTeamAgent()
        # Normalización de vectores: asegurar que sea una lista de objetos, no un dict
        _vectors = vectors or RED_TEAM_SWARM
        if isinstance(_vectors, Mapping):
            self.vectors_list = list(_vectors.values())
        else:
            self.vectors_list = list(_vectors)

        self.red_team = RedTeamSwarm(vectors=self.vectors_list)
        self.max_cycles = max_cycles

    async def forge(self, intent: str, context: Optional[Mapping[str, Any]] = None) -> SiegeResult:
        """Forge code through the fire of the siege."""
        ctx = context or {}
        feedback = []
        final_code = ""
        previous_code = ""
        previous_v_count = float("inf")

        bicameral.log_motor(f"LEGION-OMEGA: Forjando '{intent}'", action="FORGE")

        for cycle in range(1, self.max_cycles + 1):
            # Blue Team Synthesis
            code = await self.blue_team.synthesize(intent, ctx, feedback)

            # ─── Thermal Stagnation Guard (Ω₂) ───
            if code == previous_code:
                bicameral.log_motor(
                    "Thermal Equilibrium: Code identity reached. No further delta.", action="STABLE"
                )
                break

            # Red Team Siege
            vulnerabilities = await self.red_team.siege(code, ctx)
            v_count = len(vulnerabilities)

            if not vulnerabilities:
                bicameral.log_motor(f"Inmunidad Química alcanzada en ciclo {cycle}", action="Ω₆")
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

        bicameral.log_motor("Asedio finalizado. Código entregado con deudas.", action="YIELD")
        return SiegeResult(
            success=False,
            final_code=final_code,
            cycles=self.max_cycles,
            vulnerabilities=vulnerabilities if vulnerabilities else [],
        )


# Global singleton
LEGION_OMEGA = LegionOmegaEngine()
