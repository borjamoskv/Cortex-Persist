# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging

from babylon60.sica.strategy import SearchStrategy, StrategyGenome

from .types import AgentSpecialization

logger = logging.getLogger("cortex.sica.colony.specialization")


class SpecializationDetector:
    """Detect emergent specialization in a colony of agents.

    By analyzing which agents perform best with which tools
    and task types, we can assign roles and route tasks
    to the most specialized agent.
    """

    def detect(
        self,
        agents: dict[str, SearchStrategy],
    ) -> dict[str, AgentSpecialization]:
        """Analyze all agents and detect their specializations."""
        specializations: dict[str, AgentSpecialization] = {}

        for agent_id, strategy in agents.items():
            genome = strategy.genome

            # Find dominant heuristics (top by weight)
            sorted_h = sorted(
                genome.active_heuristics,
                key=lambda h: h.weight,
                reverse=True,
            )
            dominant_h = [h.name for h in sorted_h[:3]]

            # Find dominant tools
            dominant_tools = genome.tool_priority[:3]

            # Classify role based on dominant heuristics
            role, confidence = self._classify_role(dominant_h, dominant_tools, genome)

            specializations[agent_id] = AgentSpecialization(
                agent_id=agent_id,
                primary_role=role,
                role_confidence=confidence,
                dominant_tools=dominant_tools,
                dominant_heuristics=dominant_h,
                fitness_in_role=round(strategy.current_fitness, 3),
            )

        return specializations

    def recommend_routing(
        self,
        task_type: str,
        specializations: dict[str, AgentSpecialization],
    ) -> list[tuple[str, float]]:
        """Recommend which agent should handle a given task type.

        Returns list of (agent_id, suitability_score) sorted desc.
        """
        task_role_map = {
            "search": "searcher",
            "find": "searcher",
            "deploy": "deployer",
            "build": "deployer",
            "test": "verifier",
            "verify": "verifier",
            "check": "verifier",
        }

        ideal_role = task_role_map.get(task_type, "generalist")

        scored: list[tuple[str, float]] = []
        for agent_id, spec in specializations.items():
            if spec.primary_role == ideal_role:
                score = spec.fitness_in_role * spec.role_confidence
            elif spec.primary_role == "generalist":
                score = spec.fitness_in_role * 0.7
            else:
                score = spec.fitness_in_role * 0.3
            scored.append((agent_id, round(score, 3)))

        return sorted(scored, key=lambda x: x[1], reverse=True)

    def _classify_role(
        self,
        dominant_heuristics: list[str],
        dominant_tools: list[str],
        genome: StrategyGenome,
    ) -> tuple[str, float]:
        """Classify an agent's role from its genome signature."""
        search_signals = {"search", "grep", "find", "read", "analyze"}
        deploy_signals = {"deploy", "build", "mutate", "write", "create"}
        verify_signals = {"verify", "test", "check", "validate", "audit"}

        all_signals = set(dominant_tools) | set(dominant_heuristics)

        scores = {
            "searcher": len(all_signals & search_signals),
            "deployer": len(all_signals & deploy_signals),
            "verifier": len(all_signals & verify_signals),
        }

        best_role = max(scores, key=scores.get)  # type: ignore[arg-type]
        best_score = scores[best_role]

        if best_score == 0:
            return "generalist", 0.5

        total = sum(scores.values())
        confidence = best_score / total if total > 0 else 0.5

        return best_role, round(confidence, 3)
