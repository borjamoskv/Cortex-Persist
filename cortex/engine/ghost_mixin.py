"""Ghost management mixin — register and resolve ghosts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.songlines.emitter import ResonanceEmitter
from cortex.songlines.sensor import TopographicSensor
from cortex.songlines.economy import ThermalEconomy

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
    ) -> str:
        """Embed a ghost trace on a file.
        
        Args:
            reference: The entity name/id being ghosted.
            context: Semantic context (intent).
            project: Project id.
            target_file: The file to attach the ghost to. If None, uses current working context.
        """
        # 1. Enforce Thermal Economy
        root = Path.cwd()
        self._economy.validate_emission(root)
        
        # 2. Determine target file (default to some manifest if not provided)
        if not target_file:
            target_file = root / ".cortex_field"
            if not target_file.exists():
                target_file.touch()
        else:
            target_file = Path(target_file)
            
        # 3. Embed the resonance
        self._emitter.embed_ghost(
            target_file=target_file,
            intent=f"{reference}: {context}",
            project=project
        )
        
        # Return a hash-based ghost ID (compatible with old int return where possible, 
        # but songlines use string IDs)
        import hashlib
        return hashlib.sha256(f"{reference}:{project}".encode()).hexdigest()[:16]

    async def list_active_ghosts(self, root_dir: Path | None = None) -> list[dict[str, Any]]:
        """Scan the topography for all active ghosts."""
        return self._sensor.scan_field(root_dir or Path.cwd())

    async def resolve_ghost(
        self,
        ghost_id: str,
        target_entity_id: int | str = None,
        root_dir: Path | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> bool:
        """Resolve a ghost by erasing its trace from the physical landscape."""
        root = root_dir or Path.cwd()
        active = self._sensor.scan_field(root)
        
        found = False
        for ghost in active:
            if ghost['id'] == ghost_id:
                source = Path(ghost['source_file'])
                attr_name = f"user.cortex.ghost.{ghost_id}"
                self._sensor._delete_xattr(source, attr_name)
                # Also check manifest fallback if needed
                self._resolve_manifest_fallback(source, attr_name)
                found = True
                logger.info(f"Resolved ghost {ghost_id} on {source.name}")
        
        return found

    def _resolve_manifest_fallback(self, source: Path, attr_name: str):
        manifest = source.parent / ".songlines"
        if manifest.exists():
            try:
                import json
                with open(manifest, 'r') as f:
                    data = json.load(f)
                if source.name in data and attr_name in data[source.name]:
                    del data[source.name][attr_name]
                    if not data[source.name]:
                        del data[source.name]
                    with open(manifest, 'w') as f:
                        json.dump(data, f, indent=2)
            except Exception:
                pass
