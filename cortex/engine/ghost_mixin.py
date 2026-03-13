"""Ghost management mixin — register and resolve ghosts."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.songlines.sensor import GhostTrace

import aiosqlite

from cortex.songlines.economy import ThermalEconomy
from cortex.songlines.emitter import ResonanceEmitter
from cortex.songlines.sensor import TopographicSensor

logger = logging.getLogger("cortex.ghosts")


class GhostMixin:
    """Logic for managing ghost facts (mentions of entities not yet stored).

    NOW POWERED BY: Distributed Songlines (The Ghost Field).
    Ghosts live as radioactive traces on the filesystem, not in a central DB.
    """

    def __init__(self, *args, **kwargs):
        # We assume the consuming class will have a path context
        self._emitter = ResonanceEmitter()
        self._sensor = TopographicSensor()
        self._economy = ThermalEconomy(sensor=self._sensor)

    async def register_ghost(
        self,
        reference: str,
        context: str,
        project: str,
        target_file: str | Path | None = None,
        conn: aiosqlite.Connection | None = None,
        root_dir: Path | None = None,
    ) -> str:
        """Embed a ghost trace on a file.

        Args:
            reference: The entity name/id being ghosted.
            context: Semantic context (intent).
            project: Project id.
            target_file: The file to attach the ghost to. If None, uses current working context.
            root_dir: Bounded root for thermal economy field scan.
        """
        import asyncio

        def _do_register() -> str:
            nonlocal target_file
            if not target_file:
                target_file = (root_dir or Path.cwd()) / ".cortex_field"
                if not target_file.exists():
                    target_file.touch()
            else:
                target_file = Path(target_file)

            # 1. Enforce Thermal Economy. Bound to local scope to prevent O(N) scanning hang.
            eval_root = root_dir or target_file.parent
            self._economy.validate_emission(eval_root)

            # 3. Embed the resonance
            content_for_id = f"{reference}: {context}"
            self._emitter.embed_ghost(
                target_file=target_file, intent=content_for_id, project=project
            )

            # Return the same hash-based ghost ID used by the emitter
            return hashlib.sha256(content_for_id.encode()).hexdigest()[:16]

        return await asyncio.to_thread(_do_register)

    async def list_active_ghosts(self, root_dir: Path | None = None) -> list[GhostTrace]:
        """Scan the topography for all active ghosts."""
        import asyncio
        
        target_root = root_dir or Path.cwd()
        sensor = self._sensor
        
        def _list() -> list[GhostTrace]:
            return sensor.scan_field(target_root)
            
        return await asyncio.to_thread(_list)

    async def resolve_ghost(
        self,
        ghost_id: str,
        target_entity_id: int | str | None = None,
        root_dir: Path | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> bool:
        """Resolve a ghost by erasing its trace from the physical landscape."""
        import asyncio

        root = root_dir or Path.cwd()

        def _do_resolve() -> bool:
            active = self._sensor.scan_field(root)

            found = False
            for ghost in active:
                if ghost["id"] == ghost_id:
                    source = Path(ghost["source_file"])
                    attr_name = f"user.cortex.ghost.{ghost_id}"
                    self._sensor._delete_xattr(source, attr_name)
                    # Also check manifest fallback if needed
                    self._resolve_manifest_fallback(source, attr_name)
                    found = True
                    logger.info("Resolved ghost %s on %s", ghost_id, source.name)

            return found

        return await asyncio.to_thread(_do_resolve)

    def _resolve_manifest_fallback(self, source: Path, attr_name: str) -> None:
        manifest = source.parent / ".songlines"
        if manifest.exists():
            try:
                with open(manifest) as f:
                    data = json.load(f)
                if source.name in data and attr_name in data[source.name]:
                    del data[source.name][attr_name]
                    if not data[source.name]:
                        del data[source.name]
                    with open(manifest, "w") as f:
                        json.dump(data, f, indent=2)
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Failed to update manifest fallback: %s", e)
