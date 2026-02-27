# cortex/sovereign/bridge.py
"""Sovereign Bridge — The interface between CORTEX and Antigravity skills.

Provides the `SovereignBridge` class, which handles dynamic loading and
execution of Antigravity skills (aether-1, keter-omega, legion-1, etc.)
within the CORTEX environment.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Base directory for Antigravity skills
SKILLS_ROOT = Path(os.path.expanduser("~/.gemini/antigravity/skills"))


class SovereignBridge:
    """Orchestrates interaction with the Antigravity skill ecosystem."""

    def __init__(self, skills_root: Path | None = None) -> None:
        self.skills_root = skills_root or SKILLS_ROOT
        self.registry: dict[str, Any] = {}
        self._ensure_path()
        self.discover_and_load()

    def _ensure_path(self) -> None:
        """Ensure the skill parent directory is in sys.path.

        Appended rather than inserted at 0 to prevent sys.path injection attacks
        where a file in the skills root could hijack the Python standard library.
        """
        parent = str(self.skills_root.parent)
        if parent not in sys.path:
            sys.path.append(parent)
            logger.debug(f"Appended {parent} to sys.path")

    def discover_and_load(self) -> None:
        """Scan SKILLS_ROOT for skill packages and import them."""
        if not self.skills_root.exists():
            logger.warning(f"Sovereign Bridge: SKILLS_ROOT {self.skills_root} not found.")
            return

        for entry in self.skills_root.iterdir():
            if entry.is_dir() and (entry / "SKILL.md").exists():
                self._load_skill(entry.name)

        logger.info(f"Sovereign Bridge: {len(self.registry)} skills registered.")

    def _load_skill(self, skill_name: str) -> None:
        """Import a specific skill as a Python module."""
        module_path = f"antigravity.skills.{skill_name}"
        try:
            # We assume the directory name is the package name inside antigravity.skills
            module = importlib.import_module(module_path)
            self.registry[skill_name] = module
            logger.debug(f"Skill loaded: {skill_name}")
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load skill {skill_name}: {e}")

    def execute(self, skill_name: str, *args, **kwargs) -> Any:
        """Execute the 'main' entry point of a registered skill."""
        skill = self.registry.get(skill_name)
        if not skill:
            # Try to load it lazily if not found
            self._load_skill(skill_name)
            skill = self.registry.get(skill_name)

        if not skill:
            raise ImportError(f"Sovereign skill '{skill_name}' is not available.")

        if hasattr(skill, "main") and callable(skill.main):
            logger.info(f"Executing Sovereign Skill: {skill_name}")
            return skill.main(*args, **kwargs)

        # Fallback for skills that might expose other entry points
        if hasattr(skill, "run") and callable(skill.run):
            return skill.run(*args, **kwargs)

        raise AttributeError(f"Skill '{skill_name}' has no callable 'main' or 'run' entry point.")

    def list_skills(self) -> list[str]:
        """Return a list of all available skill names."""
        return list(self.registry.keys())
