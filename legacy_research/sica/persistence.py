# [C5-REAL] Exergy-Maximized
"""SICA Persistence - Genome Save/Load.

Autonomy requirement: learned strategies MUST survive restarts.
Without persistence, every agent restart resets the genome to
generation 0, discarding all evolutionary gains.

Supports:
  - JSON serialization of StrategyGenome
  - Lineage chain preservation (parent_hash tracking)
  - Atomic writes (write-to-temp + rename)
  - Optional CORTEX ledger integration for C5-REAL audit trail
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from legacy_research.sica.strategy import (
    Heuristic,
    SearchStrategy,
    StrategyGenome,
)

logger = logging.getLogger("cortex.sica.persistence")

# Default persistence directory
_DEFAULT_DIR = Path.home() / ".cortex" / "sica" / "genomes"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ── Serialization ────────────────────────────────────────────────


def genome_to_json(genome: StrategyGenome) -> dict[str, Any]:
    """Serialize a StrategyGenome to a JSON-safe dict."""
    return {
        "schema_version": 1,
        "genome_hash": genome.genome_hash,
        "generation": genome.generation,
        "parent_hash": genome.parent_hash,
        "exploration_rate": genome.exploration_rate,
        "decomposition_depth": genome.decomposition_depth,
        "error_recovery_mode": genome.error_recovery_mode,
        "tool_priority": genome.tool_priority,
        "heuristics": [
            {
                "name": h.name,
                "description": h.description,
                "weight": h.weight,
                "activation_count": h.activation_count,
                "success_count": h.success_count,
                "last_activated": h.last_activated,
            }
            for h in genome.heuristics
        ],
        "saved_at": time.time(),
    }


def genome_from_json(data: dict[str, Any]) -> StrategyGenome:
    """Deserialize a StrategyGenome from a JSON dict."""
    heuristics = [
        Heuristic(
            name=h["name"],
            description=h.get("description", ""),
            weight=h["weight"],
            activation_count=h.get("activation_count", 0),
            success_count=h.get("success_count", 0),
            last_activated=h.get("last_activated", 0.0),
        )
        for h in data.get("heuristics", [])
    ]
    return StrategyGenome(
        heuristics=heuristics,
        tool_priority=data.get("tool_priority", []),
        decomposition_depth=data.get("decomposition_depth", 3),
        exploration_rate=data.get("exploration_rate", 0.3),
        error_recovery_mode=data.get("error_recovery_mode", "retry_with_mutation"),
        generation=data.get("generation", 0),
        parent_hash=data.get("parent_hash", ""),
    )


def strategy_snapshot(strategy: SearchStrategy) -> dict[str, Any]:
    """Full snapshot: genome + mutation log + fitness history."""
    return {
        "genome": genome_to_json(strategy.genome),
        "mutation_log": [m.to_dict() for m in strategy.mutation_log],
        "current_fitness": round(strategy.current_fitness, 4),
    }


# ── File I/O ─────────────────────────────────────────────────────


def save_genome(
    genome: StrategyGenome,
    agent_id: str,
    directory: Path | str | None = None,
) -> Path:
    """Save a genome to disk with atomic write.

    File naming: {agent_id}_gen{generation}.json
    Also maintains a 'latest.json' symlink/copy.

    Returns the path to the saved file.
    """
    dir_path = Path(directory) if directory else _DEFAULT_DIR / agent_id
    _ensure_dir(dir_path)

    filename = f"{agent_id}_gen{genome.generation}.json"
    target = dir_path / filename
    tmp = target.with_suffix(".tmp")

    data = genome_to_json(genome)

    # Atomic write: tmp → rename
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(str(tmp), str(target))

    # Update latest pointer
    latest = dir_path / "latest.json"
    with open(latest.with_suffix(".tmp"), "w") as f:
        json.dump(data, f, indent=2)
    os.replace(str(latest.with_suffix(".tmp")), str(latest))

    logger.info(
        "SICA genome saved: %s (gen=%d, hash=%s)",
        target,
        genome.generation,
        genome.genome_hash,
    )
    return target


def load_genome(
    agent_id: str,
    directory: Path | str | None = None,
    generation: int | None = None,
) -> StrategyGenome | None:
    """Load a genome from disk.

    If generation is None, loads the latest.
    Returns None if no saved genome exists.
    """
    dir_path = Path(directory) if directory else _DEFAULT_DIR / agent_id

    if generation is not None:
        target = dir_path / f"{agent_id}_gen{generation}.json"
    else:
        target = dir_path / "latest.json"

    if not target.exists():
        logger.debug("No saved genome at %s", target)
        return None

    try:
        with open(target) as f:
            data = json.load(f)
        genome = genome_from_json(data)
        logger.info(
            "SICA genome loaded: %s (gen=%d, hash=%s)",
            target,
            genome.generation,
            genome.genome_hash,
        )
        return genome
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("Failed to load genome from %s: %s", target, exc)
        return None


def load_or_default(
    agent_id: str,
    directory: Path | str | None = None,
) -> SearchStrategy:
    """Load the latest genome or create a default strategy.

    This is the primary entry point for autonomous agents:
    on startup, resume from last saved state or start fresh.
    """
    from legacy_research.sica.strategy import default_genome

    genome = load_genome(agent_id, directory)
    if genome is not None:
        logger.info(
            "SICA resuming from gen=%d (hash=%s)",
            genome.generation,
            genome.genome_hash,
        )
        return SearchStrategy(genome)
    logger.info("SICA starting fresh - no saved genome for '%s'", agent_id)
    return SearchStrategy(default_genome())


def list_generations(
    agent_id: str,
    directory: Path | str | None = None,
) -> list[dict[str, Any]]:
    """List all saved generations for an agent.

    Returns metadata for each saved genome, sorted by generation.
    """
    dir_path = Path(directory) if directory else _DEFAULT_DIR / agent_id
    if not dir_path.exists():
        return []

    results = []
    for f in sorted(dir_path.glob(f"{agent_id}_gen*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
            results.append(
                {
                    "file": str(f),
                    "generation": data.get("generation", 0),
                    "genome_hash": data.get("genome_hash", ""),
                    "saved_at": data.get("saved_at", 0),
                    "heuristic_count": len(data.get("heuristics", [])),
                }
            )
        except (json.JSONDecodeError, KeyError):
            continue

    return sorted(results, key=lambda r: r["generation"])
