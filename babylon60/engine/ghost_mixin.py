# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon60.extensions.songlines.sensor import GhostTrace

import aiosqlite

from babylon60.engine.mixins.base import EngineMixinBase

__all__ = ["GhostMixin"]

logger = logging.getLogger("babylon60.ghosts")


class GhostMixin(EngineMixinBase):
    """Distributed Ghost Field - Filesystem-Embedded Entity References.

    Ghosts are radioactive traces on the filesystem (xattrs/manifest),
    not centralized DB records. Powered by the Songlines subsystem:

    - ``ResonanceEmitter``: Embeds ghost traces onto target files.
    - ``TopographicSensor``: Scans the field for active ghosts.
    - ``ThermalEconomy``: Rate-limits emissions to prevent O(N) field saturation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._emitter: Any | None = None
        self._sensor: Any | None = None
        self._economy: Any | None = None

    def _ensure_songlines(self) -> tuple[Any, Any, Any]:
        if self._emitter is None or self._sensor is None or self._economy is None:
            from babylon60.extensions.songlines.economy import ThermalEconomy
            from babylon60.extensions.songlines.emitter import ResonanceEmitter
            from babylon60.extensions.songlines.sensor import TopographicSensor

            self._emitter = ResonanceEmitter()
            self._sensor = TopographicSensor()
            self._economy = ThermalEconomy(sensor=self._sensor)
        return self._emitter, self._sensor, self._economy

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
            emitter, _sensor, economy = self._ensure_songlines()
            nonlocal target_file
            if not target_file:
                target_file = (root_dir or Path.cwd()) / ".cortex_field"
                if not target_file.exists():
                    target_file.touch()
            else:
                target_file = Path(target_file)

            # 1. Enforce Thermal Economy. Bound to local scope to prevent O(N) scanning hang.
            eval_root = root_dir or target_file.parent
            economy.validate_emission(eval_root)

            # 3. Embed the resonance
            content_for_id = f"{reference}: {context}"
            emitter.embed_ghost(target_file=target_file, intent=content_for_id, project=project)

            # Return the same hash-based ghost ID used by the emitter
            return hashlib.sha256(content_for_id.encode()).hexdigest()[:16]

        return await asyncio.to_thread(_do_register)

    async def list_active_ghosts(self, root_dir: Path | None = None) -> list[GhostTrace]:
        """Scan the topography for all active ghosts."""
        import asyncio

        target_root = root_dir or Path.cwd()
        _emitter, sensor, _economy = self._ensure_songlines()

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
            _emitter, sensor, _economy = self._ensure_songlines()
            active = sensor.scan_field(root)

            found = False
            for ghost in active:
                if ghost["id"] == ghost_id:
                    source = Path(ghost["source_file"])
                    attr_name = f"user.babylon60.ghost.{ghost_id}"
                    sensor._delete_xattr(source, attr_name)
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
