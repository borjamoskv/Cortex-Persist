"""Swarm state persistence — saves/loads evolution progress to disk.
Version: 3.0 (Atomic, Rotating Backups & Auto-Rollback)
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Optional

from cortex.extensions.evolution.agents import (
    AgentDomain,
    Mutation,
    MutationType,
    SovereignAgent,
    SubAgent,
)

logger = logging.getLogger(__name__)

# Configuración
DEFAULT_STATE_PATH: Final = Path("~/.cortex/evolution_state.json").expanduser()
MAX_BACKUPS: Final = 5
SCHEMA_VERSION: Final = 2


def _serialize_agent(a: SovereignAgent) -> dict[str, Any]:
    """Serialización profunda de un agente y sus subagentes."""
    return {
        "id": a.id,
        "domain": a.domain.name,
        "fitness": a.fitness,
        "generation": a.generation,
        "cycle_count": a._cycle_count,
        "mutations": [
            {
                "id": m.mutation_id,
                "type": m.mutation_type.name,
                "desc": m.description,
                "delta": m.delta_fitness,
                "ts": m.timestamp,
                "tags": m.epigenetic_tags,
            }
            for m in a.mutations[-20:]
        ],
        "subagents": [
            {
                "id": s.id,
                "name": s.name,
                "domain": s.domain.name,
                "fitness": s.fitness,
                "generation": s.generation,
                "params": s.parameters,
                "mutations": [
                    {
                        "id": m.mutation_id,
                        "type": m.mutation_type.name,
                        "desc": m.description,
                        "delta": m.delta_fitness,
                        "ts": m.timestamp,
                        "tags": m.epigenetic_tags,
                    }
                    for m in s.mutations[-20:]
                ],
            }
            for s in a.subagents
        ],
    }


def _get_cycle_path(base_path: Path, cycle: int) -> Path:
    return base_path.parent / f"evolution_state_cycle_{cycle:05d}.json"


def save_swarm(agents: list[SovereignAgent], cycle: int, path: Path = DEFAULT_STATE_PATH) -> bool:
    """Guarda el estado actual y rota backups antiguos."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "version": SCHEMA_VERSION,
            "cycle": cycle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": [_serialize_agent(a) for a in agents],
        }

        # Guardado atómico del backup del ciclo
        cycle_path = _get_cycle_path(path, cycle)
        temp_path = cycle_path.with_suffix(".tmp")

        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        temp_path.replace(cycle_path)

        # Actualizar puntero principal (Latest)
        shutil.copy2(cycle_path, path)

        # Rotación: mantener solo los N más recientes
        all_backups = sorted(path.parent.glob("evolution_state_cycle_*.json"))
        if len(all_backups) > MAX_BACKUPS:
            for old in all_backups[:-MAX_BACKUPS]:
                old.unlink()

        logger.info("💾 Estado guardado: ciclo %d", cycle)
        return True
    except (OSError, ValueError, TypeError) as e:
        logger.error("❌ Error al guardar: %s", e)
        return False


def load_swarm(path: Path = DEFAULT_STATE_PATH) -> Optional[tuple[list[SovereignAgent], int]]:
    """
    Carga el estado. Si falla, intenta cargar el backup más reciente disponible
    (Auto-Rollback).
    """
    if not path.parent.exists():
        return None

    # Intentamos cargar el principal primero, luego los backups ordenados por fecha descendente
    targets = [path] + sorted(
        path.parent.glob("evolution_state_cycle_*.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    for target in targets:
        if not target.exists():
            continue

        try:
            logger.debug("Intentando cargar: %s", target.name)
            with target.open("r", encoding="utf-8") as f:
                data = json.load(f)

            agents = _reconstruct_agents(data["agents"])
            cycle = data["cycle"]

            if target != path:
                logger.warning("⚠️ Recuperación exitosa usando backup: %s", target.name)
            else:
                logger.debug("📂 Estado cargado: ciclo %d", cycle)

            return agents, cycle

        except (OSError, KeyError, ValueError, TypeError) as e:
            logger.error("❌ Fallo al leer %s: %s", target.name, e)
            continue  # Probar con el siguiente backup

    logger.critical("🚨 No se encontró ningún estado o backup válido.")
    return None


def _parse_mutations(raw: list[dict]) -> list[Mutation]:
    """Parse a list of raw mutation dicts into Mutation objects."""
    mutations: list[Mutation] = []
    for m_data in raw:
        try:
            m_type = MutationType[m_data["type"]]
        except KeyError:
            continue
        mutations.append(
            Mutation(
                mutation_id=m_data["id"],
                mutation_type=m_type,
                description=m_data["desc"],
                delta_fitness=m_data["delta"],
                timestamp=m_data["ts"],
                epigenetic_tags=m_data.get("tags", {}),
            )
        )
    return mutations


def _reconstruct_subagent(s_data: dict) -> Optional[SubAgent]:
    """Reconstruct a SubAgent from a serialized dict."""
    try:
        s_domain = AgentDomain[s_data["domain"]]
    except KeyError:
        return None

    sub = SubAgent(
        id=s_data["id"],
        domain=s_domain,
        name=s_data["name"],
    )
    sub.fitness = s_data.get("fitness", 0.0)
    sub.generation = s_data.get("generation", 0)
    sub.parameters = s_data.get("params", {})
    sub.mutations = _parse_mutations(s_data.get("mutations", []))
    return sub


def _reconstruct_agents(agents_data: list[dict]) -> list[SovereignAgent]:
    """Helper para reconstruir objetos desde el dict del estado persistido."""
    sovereigns = []
    for data in agents_data:
        try:
            domain = AgentDomain[data["domain"]]
        except KeyError:
            continue

        sovereign = SovereignAgent(id=data["id"], domain=domain)
        sovereign.fitness = data.get("fitness", 0.0)
        sovereign.generation = data.get("generation", 0)
        sovereign._cycle_count = data.get("cycle_count", 0)
        sovereign.mutations = _parse_mutations(data.get("mutations", []))

        subagents = []
        for s_data in data.get("subagents", []):
            sub = _reconstruct_subagent(s_data)
            if sub is not None:
                subagents.append(sub)

        sovereign.subagents = subagents
        sovereigns.append(sovereign)

    return sovereigns
