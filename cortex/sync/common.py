"""Shared utilities and data structures for sync engine."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.sync")

AGENT_DIR = Path.home() / ".agent"
MEMORY_DIR = AGENT_DIR / "memory"
CORTEX_DIR = Path.home() / ".cortex"
SYNC_STATE_FILE = CORTEX_DIR / "sync_state.json"


@dataclass
class SyncResult:
    """Resultado de una ronda de sincronización."""

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
    """Resultado de una ronda de write-back."""

    files_written: int = 0
    files_skipped: int = 0
    items_exported: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def had_changes(self) -> bool:
        return self.files_written > 0


def load_sync_state() -> dict:
    """Carga el estado de la última sincronización (hashes de archivos)."""
    if SYNC_STATE_FILE.exists():
        try:
            return json.loads(SYNC_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_sync_state(state: dict) -> None:
    """Guarda el estado de sincronización a disco."""
    SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SYNC_STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def file_hash(path: Path) -> str:
    """Calcula SHA-256 de un archivo para detectar cambios."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, content: str) -> None:
    """Escritura atómica: escribe a temp + os.replace().

    Evita corrupción si el proceso muere a mitad de escritura.
    En POSIX, os.replace() es atómico dentro del mismo filesystem.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Crear temp en el mismo directorio para garantizar mismo filesystem
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
        # Limpiar temp si falla el replace
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def get_existing_contents(
    engine: CortexEngine,
    project: str | None = None,
    fact_type: str | None = None,
) -> set[str]:
    """Obtiene set de contenidos existentes para deduplicación rápida.

    Args:
        engine: Instancia de CortexEngine.
        project: Filtrar por proyecto. None = cualquiera.
        fact_type: Filtrar por tipo. None = cualquiera.

    Returns:
        Set de strings con el contenido de cada fact existente.
    """
    conn = engine._get_sync_conn()
    query = "SELECT content FROM facts WHERE valid_until IS NULL"
    params: list = []

    if project:
        query += " AND project = ?"
        params.append(project)
    if fact_type:
        query += " AND fact_type = ?"
        params.append(fact_type)

    rows = conn.execute(query, params).fetchall()
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


def db_content_hash(engine: CortexEngine, fact_type: str | None = None) -> str:
    """Calcula SHA-256 del contenido actual en DB para un tipo de fact.

    Esto permite detectar si la DB ha cambiado desde el último write-back
    sin necesidad de comparar fila por fila.
    """
    conn = engine._get_sync_conn()
    if fact_type:
        rows = conn.execute(
            "SELECT id, content, meta, valid_from FROM facts "
            "WHERE fact_type = ? AND valid_until IS NULL ORDER BY id",
            (fact_type,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, content, meta, valid_from FROM facts WHERE valid_until IS NULL ORDER BY id"
        ).fetchall()

    # Serializar el contenido completo como un hash determinista
    hasher = hashlib.sha256()
    for row in rows:
        hasher.update(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}\n".encode())
    return hasher.hexdigest()


def calculate_fact_diff(
    existing: set[str], candidates: list[dict], content_generator: Any
) -> list[tuple[str, dict]]:
    """Calcula qué hechos son nuevos comparándolos con lo existente."""
    results = []
    for c in candidates:
        content = content_generator(c)
        if content not in existing:
            results.append((content, c))
    return results
