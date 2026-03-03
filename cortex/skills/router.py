"""
Skill Routing Engine — Capa base de ejecución Soberana (MOSKV-1).

Transforma intención en invocación de la capability correcta.
Enruta dinámicamente según el grafo de dependencias de la SkillRegistry.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.skills.registry import SkillManifest, SkillRegistry

logger = logging.getLogger(__name__)


class SkillRouter:
    """
    Orquestador base que determina qué skill(s) debe ejecutarse para resolver una intención.
    Abandona la ejecución lineal (fases hardcodeadas) en favor del enrutamiento basado en capabilities.
    """

    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self.registry = registry or SkillRegistry().load()

    def route_intent(self, intent: str, context: dict[str, Any] | None = None) -> list[SkillManifest]:
        """
        Analiza la intención cruda del operador (TBD: usar LLM/Noosphere) o heuristics,
        y devuelve la secuencia de manifests óptima para ejecutarla.

        (Placeholder inicial: búsqueda simple usando metadata del manifest).
        """
        # Búsqueda semántica usando el motor de búsqueda que implementamos.
        # Si la intención nombra explícitamente el alias o comando, lo matcheamos primero.
        candidates = self.registry.search(intent)

        # Si tenemos un "god mode" o transcendent skill, lo priorizamos si corresponde.
        if "crea" in intent.lower() or "build" in intent.lower() or "proyecto" in intent.lower():
            # Intentamos forzar Keter o Aether/Genesis según las keywords.
            manifest = self.registry.get("keter-omega") or self.registry.get("aether-1")
            if manifest and manifest not in candidates:
                candidates.insert(0, manifest)

        if not candidates:
            logger.warning("[ROUTER] No skills found for intent: %s", intent)
            return []

        # Retornamos el mejor match (simple logic p.ej., primera) o el manifold de ejecución
        # En el futuro: Construiremos el grafo y aplicaremos topologically sort de dependencias.
        return candidates[:3]  # Límite arbitrario para pruebas

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
                    logger.warning(f"Dependency {dep_slug} for {node.slug} not found.")

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
