# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from babylon60.crypto.hash_registry import cortex_hash

__all__ = [
    "AGENT_DIR",
    "CORTEX_DIR",
    "MEMORY_DIR",
    "SYNC_STATE_FILE",
    "SyncResult",
    "WritebackResult",
    "atomic_write",
    "calculate_fact_diff",
    "db_content_hash",
    "file_hash",
    "get_existing_contents",
    "load_sync_state",
    "save_sync_state",
]

if TYPE_CHECKING:
    from babylon60.engine import CortexEngine

logger = logging.getLogger("babylon60_extensions.sync")

from babylon60.core.paths import (
    AGENT_DIR,
    CORTEX_DIR,
    MEMORY_DIR,
    SYNC_STATE_FILE,
)


def _runtime_path(name: str, default: Path) -> Path:
    sync_module = sys.modules.get("cortex_extensions.sync")
    if sync_module is None:
        return default
    value = getattr(sync_module, name, default)
    return value if isinstance(value, Path) else Path(value)


def runtime_memory_dir() -> Path:
    return _runtime_path("MEMORY_DIR", MEMORY_DIR)


def runtime_sync_state_file() -> Path:
    return _runtime_path("SYNC_STATE_FILE", SYNC_STATE_FILE)


@dataclass
class SyncResult:
    """Result of a synchronization round."""

    synced_at: str = ""
    facts_synced: int = 0
    ghosts_synced: int = 0
    errors_synced: int = 0
    bridges_synced: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.facts_synced + self.ghosts_synced + self.errors_synced + self.bridges_synced

    @property
    def had_changes(self) -> bool:
        return self.total > 0


@dataclass
class WritebackResult:
    """Result of a write-back round."""

    files_written: int = 0
    files_skipped: int = 0
    items_exported: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def had_changes(self) -> bool:
        return self.files_written > 0


def load_sync_state() -> dict:
    """Loads the state of the last synchronization (file hashes)."""
    sync_state_file = runtime_sync_state_file()
    if sync_state_file.exists():
        try:
            return json.loads(sync_state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_sync_state(state: dict) -> None:
    """Saves the synchronization state to disk."""
    sync_state_file = runtime_sync_state_file()
    sync_state_file.parent.mkdir(parents=True, exist_ok=True)
    sync_state_file.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def file_hash(path: Path) -> str:
    """Calculates SHA-256 of a file to detect changes."""
    if not path.exists():
        return ""
    return cortex_hash(path.read_bytes())


def atomic_write(path: Path, content: str) -> None:
    """Atomic write: writes to temp + os.replace().

    Prevents corruption if the process dies mid-write.
    In POSIX, os.replace() is atomic within the same filesystem.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create temp in the same directory to guarantee the same filesystem
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(path))
    except OSError:
        # Clean up temp if replace fails
        try:
            os.unlink(tmp_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Suppressed exception: %s", exc)
        raise


async def get_existing_contents(
    engine: CortexEngine,
    project: str | None = None,
    fact_type: str | None = None,
) -> set[str]:
    """Retrieves a set of existing contents for fast deduplication.

    Args:
        engine: CortexEngine instance.
        project: Filter by project. None = any.
        fact_type: Filter by fact type. None = any.

    Returns:
        Set of strings containing the content of each existing fact.
    """
    async with engine.session() as conn:
        query = "SELECT content FROM facts WHERE valid_until IS NULL"
        params: list = []

        if project:
            query += " AND project = ?"
            params.append(project)
        if fact_type:
            query += " AND fact_type = ?"
            params.append(fact_type)

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        result = {row[0] for row in rows}

    # Normalize legacy-prefixed entries for backward-compat dedup.
    # Old syncs stored "DECISION: X | RAZON: Y"; new syncs store "X".
    # Both forms must be in the set to prevent re-insertion.
    normalized: set[str] = set()
    for c in result:
        stripped = c
        if stripped.startswith("DECISION: "):
            stripped = stripped.replace("DECISION: ", "", 1)
        if " | RAZON:" in stripped:
            stripped = stripped.rsplit(" | RAZON:", 1)[0].strip()
        if stripped != c:
            normalized.add(stripped)
    return result | normalized


async def db_content_hash(engine: CortexEngine, fact_type: str | None = None) -> str:
    """Calculates SHA-256 of the current DB content for a fact type.

    This allows detecting if the DB has changed since the last write-back
    without needing row-by-row comparison.
    """
    async with engine.session() as conn:
        if fact_type:
            cursor = await conn.execute(
                "SELECT id, content, metadata, valid_from FROM facts "
                "WHERE fact_type = ? AND valid_until IS NULL ORDER BY id",
                (fact_type,),
            )
        else:
            cursor = await conn.execute(
                "SELECT id, content, metadata, valid_from FROM facts "
                "WHERE valid_until IS NULL ORDER BY id"
            )
        rows = await cursor.fetchall()

    # Serialize the complete content as a deterministic hash
    hasher = hashlib.sha256()
    for row in rows:
        hasher.update(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}\n".encode())
    return hasher.hexdigest()


def calculate_fact_diff(
    existing: set[str], candidates: list[dict], content_generator: Any
) -> list[tuple[str, dict]]:
    """Calculates which facts are new by comparing them against the existing ones."""
    results = []
    for c in candidates:
        content = content_generator(c)
        if content not in existing:
            results.append((content, c))
    return results
