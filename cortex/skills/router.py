"""
Skill Routing Engine — Capa base de ejecución Soberana (MOSKV-1).

Transforma intención en invocación de la capability correcta.
Enruta dinámicamente según el grafo de dependencias de la SkillRegistry.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from cortex.memory.metamemory import MetamemoryMonitor
from cortex.memory.procedural import ProceduralMemory
from cortex.skills.registry import SkillManifest, SkillRegistry

logger = logging.getLogger(__name__)

# Minimum Procedural FOK to allow execution.
# Below this, the router declares ignorance rather than hallucinating a skill.
_FOK_GATE: Final[float] = 0.35


class SkillRouter:
    """
    Orquestador base que determina qué skill(s) debe ejecutarse para resolver una intención.
    Abandona la ejecución lineal (fases hardcodeadas) en favor del enrutamiento basado en capabilities.
    """

    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self.registry = registry or SkillRegistry().load()
        self.metamemory = MetamemoryMonitor()
        self.procedural_memory = ProceduralMemory()

    def route_intent(
        self, intent: str, context: dict[str, Any] | None = None
    ) -> list[SkillManifest]:
        """
        Analiza la intención cruda del operador (TBD: usar LLM/Noosphere) o heuristics,
        y devuelve la secuencia de manifests óptima para ejecutarla.

        (Placeholder inicial: búsqueda simple usando metadata del manifest).
        """
        # Búsqueda semántica usando el motor de búsqueda que implementamos.
        # Si la intención nombra explícitamente el alias o comando, lo matcheamos primero.
        candidates = self.registry.search(intent)

        # ── Procedural Metamemory Gate ────────────────────────────────────
        # Augment each candidate with its full capability surface before scoring.
        # This lets FOK see *what a skill declares it can do* (not just its name).
        augmented_candidates = []
        for m in candidates:
            caps = [c.name for c in getattr(m, "capabilities", [])]
            tags = getattr(m, "tags", [])
            # Synthesize a rich surface string the FOK heuristic can match against
            m.__dict__.update({"_fok_surface": " ".join([m.name, m.description, *caps, *tags])})
            augmented_candidates.append(m)

        judgment = self.metamemory.judge_procedural_fok(intent, augmented_candidates)
        if judgment.fok_score < _FOK_GATE:
            if judgment.tip_of_tongue:
                logger.warning(
                    "[ROUTER] Tip-of-Tongue: conceptos relacionados detectados pero sin skill exacto para: '%s'",
                    intent,
                )
            else:
                logger.warning(
                    "[ROUTER] Unknown Capability: FOK=%.3f < %.2f para: '%s'",
                    judgment.fok_score,
                    _FOK_GATE,
                    intent,
                )
            return []

        # Si tenemos un "god mode" o transcendent skill, lo priorizamos si corresponde.
        if "crea" in intent.lower() or "build" in intent.lower() or "proyecto" in intent.lower():
            # Intentamos forzar Keter o Aether/Genesis según las keywords.
            manifest = self.registry.get("keter-omega") or self.registry.get("aether-1")
            if manifest and manifest not in candidates:
                candidates.insert(0, manifest)

        if not candidates:
            logger.warning("[ROUTER] No skills found for intent: %s", intent)
            return []

        # Re-rankeamos candidatos usando ProceduralMemory (Striatal valuation)
        # Auto-seed transcendent skills as permanent (no temporal decay)
        for m in candidates:
            if getattr(m, "is_transcendent", False) and not self.procedural_memory.get_engram(
                m.slug
            ):
                self.procedural_memory.record_execution(
                    m.slug,
                    success=True,
                    latency_ms=0.0,
                    permanent=True,
                )

        def _striatal_key(manifest: SkillManifest) -> float:
            engram = self.procedural_memory.get_engram(manifest.slug)
            return engram.striatal_value if engram else 0.5

        candidates.sort(key=_striatal_key, reverse=True)

        return candidates[:3]

    def resolve_dependencies(self, manifest: SkillManifest) -> list[SkillManifest]:
        """
        Resuelve recursivamente el DAG de dependencias de una Skill,
        asegurando que se ejecutan los pre-requisitos antes.
        """
        sequence: list[SkillManifest] = []
        visited: set[str] = set()

        def _dfs(node: SkillManifest) -> None:
            if node.slug in visited:
                return
            visited.add(node.slug)
            for dep_slug in node.depends_on:
                dep_manifest = self.registry.get(dep_slug)
                if dep_manifest:
                    _dfs(dep_manifest)
                else:
                    logger.warning("Dependency %s for %s not found.", dep_slug, node.slug)

            for req in node.requirements:
                req_manifest = self.registry.get(req.skill_name)
                # O podríamos buscar por require.capability
                if req_manifest:
                    _dfs(req_manifest)

            sequence.append(node)

        _dfs(manifest)
        return sequence

    def create_execution_plan(self, intent: str) -> list[SkillManifest]:
        """
        Crea un plan lineal y ordenado de ejecución (Pipeline).
        """
        candidates = self.route_intent(intent)
        if not candidates:
            return []

        # Tomamos el principal candidato
        primary = candidates[0]
        logger.info("[ROUTER] Primary elected: %s", primary.name)

        return self.resolve_dependencies(primary)
