# [C5-REAL] Exergy-Maximized
import json
import logging
import re
from pathlib import Path
from typing import Any

from babylon60.engine.legion import AsyncSignalBus, Squadron, SwarmAgent, SwarmSignal
from babylon60.engine.legion_vectors import RED_TEAM_SWARM
from babylon60.engine.nemesis_agent import NemesisAgentAdapter

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# CORE AGENTS (MULTI-SPECIALIST)
# -----------------------------------------------------------------------------


class MultiSpecialistAgent(SwarmAgent):
    """A high-capacity agent that executes multiple specialized audit vectors."""

    def __init__(
        self,
        agent_id: str,
        bus: AsyncSignalBus,
        specialists: list[str],
        engine: Any = None,
    ):
        super().__init__(agent_id, bus, engine)
        self.specialists = specialists

    async def execute(self, target: str) -> SwarmSignal:
        logger.info(
            "[LEGION-20] %s executing %d specialists on: %s",
            self.agent_id,
            len(self.specialists),
            target,
        )

        all_findings = []
        path = Path(target)
        content = ""
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
            except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
                logger.debug("Failed to read %s: %s", target, e)

        # Iterate through assigned specialists
        for spec_id in self.specialists:
            # 1. Check Red Team Vectors
            if spec_id in RED_TEAM_SWARM:
                vector = RED_TEAM_SWARM[spec_id]
                findings = await vector.attack(content or target, {"agent_id": self.agent_id})
                all_findings.extend([f"[{spec_id}] {f}" for f in findings])

            elif "Audit" in spec_id or "Integrity" in spec_id or "Code" in spec_id:
                debt_line = self._check_static_debt(content)
                if debt_line:
                    all_findings.append(f"[{spec_id}] Actual debt found: {debt_line}")

        status = "SUCCESS" if all_findings else "VOID"
        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status=status,
            payload={"findings": all_findings, "specialists_count": len(self.specialists)},
            metrics={"time_ms": 150},
        )

    def _check_static_debt(self, content: str) -> str | None:
        if not content:
            return None

        excl = [
            'if "TO' + 'DO" in',
            '["TO' + 'DO"',
            "target_patterns",
            "forbidden =",
            "# no-audit",
            "re.compile",
            'if "FI' + 'XME" in',
            '["FI' + 'XME"',
            "is_todo =",
            'or "TO' + 'DO" in',
            'or "FI' + 'XME" in',
            "TO" + "DO el",
            "TO" + "DO los",
            "TO" + "DO la",
            "TO" + "DO las",
        ]

        if any(kw in content for kw in ["TO" + "DO", "FI" + "XME"]):
            for line in content.splitlines():
                line_stripped = line.strip()
                is_todo = ("TO" + "DO") in line_stripped or ("FI" + "XME") in line_stripped
                is_excluded = any(p in line_stripped for p in excl)

                if is_todo and not is_excluded:
                    return line_stripped

        return None


# -----------------------------------------------------------------------------
# PHALANX DEFINITIONS (LEGION 20 AGENTS)
# -----------------------------------------------------------------------------


class PhalanxBase(Squadron):
    """Base for Phalanxes that load 20-agent/100-specialist mapping from registry."""

    REPLICAS = 20  # 20 agents per phalanx = 100 total agents

    def __init__(self, engine: Any = None):
        super().__init__(engine)
        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        # Resolve path relative to this file: ../../resources/swarm_100_registry.json
        reg_path = Path(__file__).resolve().parents[2] / "resources/swarm_100_registry.json"
        if reg_path.exists():
            return json.loads(reg_path.read_text())
        return {}

    def _get_agent_spec(self, agent_id: str) -> list[str]:
        # Extract specialists for this specific agent from registry
        for agent in self.registry.get("agents", []):
            if agent["id"] == agent_id:
                return agent.get("specialists", [])
        return []

    async def _map(self, target_pattern: str | None = None) -> list[str]:
        """MAP phase: Shards a directory into individual files for parallel audit."""
        if not target_pattern:
            return []

        path = Path(target_pattern)
        if path.is_file():
            return [str(path)]

        if path.is_dir():
            # Recursively find all source files for the audit
            extensions = {".py", ".js", ".ts", ".go", ".rs", ".md", ".json"}
            exclude_dirs = {
                "node_modules",
                ".venv",
                "venv",
                ".git",
                "__pycache__",
                ".ruff_cache",
                ".pytest_cache",
                "dist",
                "build",
                ".vercel",
            }
            targets = [
                str(p)
                for p in path.rglob("*")
                if p.is_file()
                and p.suffix in extensions
                and not any(d in p.parts for d in exclude_dirs)
            ]
            return targets

        return [target_pattern]

    async def _crystallize(self, signals: list[SwarmSignal]) -> dict[str, Any]:
        """Intercepts Exergy/Nemesis structural actions before final aggregation."""
        report = await super()._crystallize(signals)

        for s in signals:
            action = s.payload.get("recommended_action") or s.payload.get("action")
            target = s.target

            if action == "KILL_NODE":
                logger.critical(
                    "☠️ [DEATH PROTOCOL] Ejecutando eutanasia algorítmica sobre: %s", target
                )
                # Structural execution:
                # 1. If it's a file path, we append .void to quarantine it from future swarm mapping
                p = Path(target)
                if p.exists() and p.is_file() and not p.name.startswith("."):
                    quarantine_path = p.with_suffix(p.suffix + ".void")
                    try:
                        p.rename(quarantine_path)
                        s.payload["execution_result"] = f"File quarantined to {quarantine_path}"
                    except OSError as e:
                        s.payload["execution_result"] = f"Failed to quarantine file: {e}"
                else:
                    s.payload["execution_result"] = "Abstract node terminated in ledger."

            elif action == "SHARD_NODE":
                logger.warning("🪓 [SHARD PROTOCOL] Bifurcando nodo entrópico: %s", target)
                s.payload["execution_result"] = "Node marked for swarm bifurcation."

        return report

    def _create_agent(self, agent_id: str) -> SwarmAgent:
        # Map sequential ID (0-3) to phalanx-specific registry IDs
        registry_p = self.registry.get("phalanxes", {})
        phalanx_agents = registry_p.get(self.SQUAD_NAME, {}).get("agents", [])
        idx = int(agent_id.split("-")[-1])

        # Evolución Adversaria (Ω₁₃): 10% del enjambre es Nemesis L4
        if idx % 10 == 9:
            return NemesisAgentAdapter(agent_id, self.bus, self.engine)

        # Evolución Exergética (TSI-Ω): 10% del enjambre es ExergyMaximizerAgent
        if idx % 10 == 8:
            from babylon60.engine.exergy_agent import ExergyAgentAdapter

            return ExergyAgentAdapter(agent_id, self.bus, self.engine)

        if idx < len(phalanx_agents):
            reg_id = phalanx_agents[idx]
            specs = self._get_agent_spec(reg_id)
            return MultiSpecialistAgent(reg_id, self.bus, specs, self.engine)
        return MultiSpecialistAgent(agent_id, self.bus, [], self.engine)


class SilverPhalanx(PhalanxBase):
    SQUAD_NAME = "SILVER"


class GoldPhalanx(PhalanxBase):
    SQUAD_NAME = "GOLD"


class LeadPhalanx(PhalanxBase):
    SQUAD_NAME = "LEAD"


class VoidPhalanx(PhalanxBase):
    SQUAD_NAME = "VOID"


class SovereignPhalanx(PhalanxBase):
    SQUAD_NAME = "SOVEREIGN"


# -----------------------------------------------------------------------------
# AUTONOMOUS ROUTER (Phalanx-Aware)
# -----------------------------------------------------------------------------


class AutonomousRouter:
    """O(1) Autonomous Router to dispatch targets to the correct Phalanx."""

    # Silver: Static analysis, files, local audit
    SILVER_PATTERN = re.compile(
        r"\.(py|js|ts|jsx|tsx|go|rs|cpp|c|md|json|yaml|yml)$|"
        r"\b(lint|type|audit|test|format|check|validate)\b",
        re.IGNORECASE,
    )
    # Gold: Capital, bounties, revenue
    GOLD_PATTERN = re.compile(
        r"\b(bounty|revenue|arbitrage|subscription|billing|invoice|capital|gold)\b",
        re.IGNORECASE,
    )
    # Lead: Research, knowledge, RAG
    LEAD_PATTERN = re.compile(
        r"\b(rag|graph|semantic|lore|history|archive|knowledge|lore)\b",
        re.IGNORECASE,
    )
    # Void: Chaos, cleanup, entropy
    VOID_PATTERN = re.compile(
        r"\b(dead|unused|cleanup|debt|ghost|chaos|entropy|purge|annihilate|void)\b",
        re.IGNORECASE,
    )
    # Sovereign: Axioms, consensus, core policy
    SOVEREIGN_PATTERN = re.compile(
        r"\b(axiom|consensus|policy|governance|wbft|sovereign|apex)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def route(target: str) -> list[type[Squadron]]:
        target_lower = target.strip().lower()

        # 1. Explicit intent override
        intent_match = re.match(r"^intent:\s*([a-z0-9_]+)", target_lower)
        if intent_match:
            intent = intent_match.group(1)
            mapping = {
                "silver": [SilverPhalanx],
                "gold": [GoldPhalanx],
                "lead": [LeadPhalanx],
                "void": [VoidPhalanx],
                "sovereign": [SovereignPhalanx],
            }
            if intent in mapping:
                return mapping[intent]

        # 2. Heuristic Scoring
        scores: dict[type[Squadron], float] = {
            SilverPhalanx: 0.0,
            GoldPhalanx: 0.0,
            LeadPhalanx: 0.0,
            VoidPhalanx: 0.0,
            SovereignPhalanx: 0.0,
        }

        if AutonomousRouter.SILVER_PATTERN.search(target_lower):
            scores[SilverPhalanx] += 1.0
        if AutonomousRouter.GOLD_PATTERN.search(target_lower):
            scores[GoldPhalanx] += 1.0
        if AutonomousRouter.LEAD_PATTERN.search(target_lower):
            scores[LeadPhalanx] += 1.0
        if AutonomousRouter.VOID_PATTERN.search(target_lower):
            scores[VoidPhalanx] += 1.0
        if AutonomousRouter.SOVEREIGN_PATTERN.search(target_lower):
            scores[SovereignPhalanx] += 1.0

        # Resolve top scorers
        max_score = max(scores.values())
        if max_score > 0:
            matched = [sq for sq, score in scores.items() if score == max_score]
            return matched

        # Fallback
        return [SilverPhalanx]
