"""Sync Engine: Read (Memory -> DB)."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import TYPE_CHECKING

from cortex.sync.common import (
    MEMORY_DIR,
    SyncResult,
    calculate_fact_diff,
    file_hash,
    get_existing_contents,
    load_sync_state,
    save_sync_state,
)
from cortex.sync.system import sync_system
from cortex.memory.temporal import now_iso

__all__ = ["sync_memory"]

if TYPE_CHECKING:
    from pathlib import Path

    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.sync")


def _sync_file(
    engine: CortexEngine,
    path: Path,
    state_key: str,
    state: dict,
    sync_fn,
    result: SyncResult,
) -> None:
    """Hash-check a single file and sync it if changed."""
    try:
        fhash = file_hash(path)
        if fhash and fhash != state.get(state_key):
            sync_fn(engine, path, result)
            state[state_key] = fhash
    except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
        result.errors.append(f"{path.name}: {e}")
        logger.error("Syncing %s failed: %s", path.name, e)


def sync_memory(engine: CortexEngine) -> SyncResult:
    """Sincroniza ~/.agent/memory/ → CORTEX DB.

    Solo importa archivos que han cambiado desde la última sincronización.
    Usa hashes SHA-256 para detectar cambios. Idempotente y no destructivo.

    Args:
        engine: Instancia inicializada de CortexEngine.

    Returns:
        SyncResult con estadísticas de la sincronización.
    """
    result = SyncResult(synced_at=now_iso())
    state = load_sync_state()

    if not MEMORY_DIR.exists():
        result.errors.append(f"Directorio de memoria no encontrado: {MEMORY_DIR}")
        return result

    _sync_file(engine, MEMORY_DIR / "ghosts.json", "ghosts_hash", state, _sync_ghosts, result)
    _sync_file(engine, MEMORY_DIR / "system.json", "system_hash", state, sync_system, result)
    _sync_file(
        engine, MEMORY_DIR / "mistakes.jsonl", "mistakes_hash", state, _sync_mistakes, result
    )
    _sync_file(engine, MEMORY_DIR / "bridges.jsonl", "bridges_hash", state, _sync_bridges, result)

    # Guardar estado para la próxima ejecución
    state["last_sync"] = result.synced_at
    save_sync_state(state)

    if result.had_changes:
        logger.info(
            "Sincronización completada: %d hechos nuevos (%d ghosts, %d errores, %d bridges)",
            result.total,
            result.ghosts_synced,
            result.errors_synced,
            result.bridges_synced,
        )
    else:
        logger.debug("Sin cambios detectados desde la última sincronización")

    return result


def _sync_ghosts(engine: CortexEngine, path: Path, result: SyncResult) -> None:
    """Sincroniza ghosts.json — estado actual de cada proyecto fantasma."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result.errors.append(f"Error leyendo ghosts.json: {e}")
        return

    # Deprecar ghosts anteriores (son snapshots temporales)
    conn = engine._get_sync_conn()
    try:
        conn.execute(
            "UPDATE facts SET valid_until = ? WHERE fact_type = 'ghost' AND valid_until IS NULL",
            (result.synced_at,),
        )
        conn.commit()
    except sqlite3.Error as e:
        result.errors.append(f"Error deprecando ghosts antiguos: {e}")

    # Insertar snapshot actual de cada proyecto
    for project_name, ghost_data in data.items():
        content = (
            f"GHOST: {project_name} | "
            f"Última tarea: {ghost_data.get('last_task', 'desconocida')} | "
            f"Estado: {ghost_data.get('mood', 'desconocido')} | "
            f"Bloqueado: {ghost_data.get('blocked_by', 'no')}"
        )
        try:
            engine.store_sync(
                project=project_name,
                content=content,
                fact_type="ghost",
                tags=["ghost", "proyecto-estado", ghost_data.get("mood", "")],
                confidence="verified",
                source="sync-agent-memory",
                meta=ghost_data,
                valid_from=ghost_data.get("timestamp"),
            )
            result.ghosts_synced += 1
        except (sqlite3.Error, ValueError) as e:
            result.errors.append(f"Error sincronizando ghost {project_name}: {e}")


def _sync_mistakes(engine: CortexEngine, path: Path, result: SyncResult) -> None:
    """Sincroniza mistakes.jsonl — memoria de errores."""
    existing = get_existing_contents(engine, None, fact_type="error")
    lines = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]

    def generate_content(m):
        return (
            f"ERROR: {m.get('error', 'desconocido')} | "
            f"CAUSA: {m.get('root_cause', 'desconocida')} | "
            f"FIX: {m.get('fix', 'desconocido')}"
        )

    new_mistakes = calculate_fact_diff(existing, lines, generate_content)
    for content, m in new_mistakes:
        try:
            engine.store_sync(
                project=m.get("project", "__system__"),
                content=content,
                fact_type="error",
                tags=m.get("tags", []),
                confidence="verified",
                source="sync-agent-memory",
                valid_from=m.get("date"),
                meta=m,
            )
            result.errors_synced += 1
            existing.add(content)
        except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
            result.errors.append(f"Error sync mistake: {e}")


def _sync_bridges(engine: CortexEngine, path: Path, result: SyncResult) -> None:
    """Sincroniza bridges.jsonl — conexiones entre proyectos."""
    existing = get_existing_contents(engine, "__bridges__", fact_type="bridge")
    lines = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]

    def generate_content(b):
        return (
            f"BRIDGE: {b.get('from', '?')} → {b.get('to', '?')} | "
            f"Patrón: {b.get('pattern', '?')} | "
            f"Nota: {b.get('note', '')}"
        )

    new_bridges = calculate_fact_diff(existing, lines, generate_content)
    for content, b in new_bridges:
        try:
            engine.store_sync(
                project="__bridges__",
                content=content,
                fact_type="bridge",
                tags=[b.get("from", ""), b.get("to", ""), b.get("pattern", "")],
                confidence="verified",
                source="sync-agent-memory",
                valid_from=b.get("date"),
                meta=b,
            )
            result.bridges_synced += 1
            existing.add(content)
        except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
            result.errors.append(f"Error sync bridge: {e}")
