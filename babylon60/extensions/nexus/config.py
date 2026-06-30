# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Singularity Nexus Configuration Parser.

Parses the `.nexus.yaml` or `cortex_nexus_map.yaml` files defining global
symlink topologies to enforce across `10_PROJECTS`.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger("babylon60.nexus.config")


@dataclass
class NexusConfig:
    """Represents a parsed Nexus topology."""

    target_workspaces: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)


def load_nexus_config(config_path: str | Path) -> NexusConfig:
    """
    Load and parse a YAML Nexus configuration file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        NexusConfig instance.
    """
    config_path = Path(config_path)

    if not config_path.exists():
        logger.warning(f"[Nexus] Configuration file not found: {config_path}")
        return NexusConfig()

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return NexusConfig()

        workspaces = data.get("target_workspaces", [])
        artifacts = data.get("artifacts", [])

        # Expand ~ to home directory in workspaces
        expanded_workspaces = [os.path.expanduser(w) for w in workspaces]

        return NexusConfig(target_workspaces=expanded_workspaces, artifacts=artifacts)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[Nexus] Failed to parse {config_path}: {e}")
        return NexusConfig()
