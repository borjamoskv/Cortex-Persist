"""Support helpers for the cognitive memory manager."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from typing import Any

from cortex.database.core import connect as connect_db

logger = logging.getLogger("cortex.memory.manager")


def init_dynamic_space(manager: Any) -> Any | None:
    """Initialize semantic RAM if the optional module is healthy."""
    if not manager._l2:
        return None
    try:
        from cortex.memory.semantic_ram import DynamicSemanticSpace

        return DynamicSemanticSpace(manager._l2, manager=manager)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Dynamic semantic space unavailable: %s", exc)
        return None


def init_hologram(manager: Any) -> Any | None:
    """Initialize the RAM hologram without blocking manager startup."""
    if not manager._l2:
        return None
    try:
        from cortex.memory.hologram import HolographicMemory

        return HolographicMemory(manager._l2)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Holographic memory unavailable: %s", exc)
        return None


def init_metamemory() -> Any | None:
    """Initialize metamemory telemetry if the module is available."""
    try:
        from cortex.memory.metamemory import MetamemoryMonitor

        return MetamemoryMonitor()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Metamemory monitor unavailable: %s", exc)
        return None


def init_resonance_gate(manager: Any) -> Any | None:
    """Initialize the critical resonance validator lazily."""
    if not manager._l2:
        return None

    sensor = None
    try:
        from cortex.extensions.songlines.sensor import TopographicSensor

        sensor = TopographicSensor()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Topographic sensor unavailable for resonance gate: %s", exc)

    try:
        from cortex.memory.resonance import AdaptiveResonanceGate

        return AdaptiveResonanceGate(
            vector_store=manager._l2,
            songline_sensor=sensor,
            endocrine=manager._endocrine,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Resonance gate unavailable during startup: %s", exc)
        return None


def start_bg_workers(manager: Any) -> None:
    """Initialize persistent background workers for L2 compression."""
    if manager._bg_workers:
        return

    num_workers = min(3, max(1, manager._max_bg_tasks // 10))
    for worker_id in range(num_workers):
        task = asyncio.create_task(compression_worker_loop(manager, worker_id))
        manager._bg_workers.append(task)


async def compression_worker_loop(manager: Any, worker_id: int) -> None:
    """Persistent worker loop consuming from the background queue."""
    from cortex.memory import manager as manager_module

    while True:
        try:
            overflowed, session_id, tenant_id, project_id = await manager._bg_queue.get()
            try:
                await manager_module.compress_and_store(
                    manager,
                    overflowed,
                    session_id,
                    tenant_id,
                    project_id,
                )
            except (ValueError, TypeError, RuntimeError, OSError) as exc:
                logger.error("MemoryManager: Worker %d failed compression: %s", worker_id, exc)
            finally:
                manager._bg_queue.task_done()
        except asyncio.CancelledError:
            raise
        except (ValueError, TypeError, RuntimeError, OSError) as exc:
            logger.error("MemoryManager: Worker %d encountered fatal error: %s", worker_id, exc)
            await asyncio.sleep(1)


async def check_deduplication(
    manager: Any,
    tenant_id: str,
    project_id: str,
    content: str,
    subject_hash: str,
) -> dict[str, str | None]:
    """Check for exact matches or epistemological conflicts."""
    if not content or not content.strip():
        return {"status": "empty", "id": None}

    if native_conflict := await manager._arbiter.check_async(subject_hash):
        logger.info("⚡ [SILICON-HIT] native conflict detection for %s", subject_hash)
        return {"status": "conflict", "id": "native:conflict", "content": native_conflict}

    if not manager._l2:
        return {"status": "new", "id": None}

    def _sync_check() -> dict[str, str | None]:
        db_path = getattr(manager._l2, "_db_path", None)
        conn: sqlite3.Connection | None = None
        try:
            if db_path is not None:
                conn = connect_db(
                    str(db_path),
                    read_only=True,
                    row_factory=sqlite3.Row,
                )
            elif hasattr(manager._l2, "_get_conn"):
                conn = manager._l2._get_conn()
            if conn is None:
                return {"status": "new", "id": None}

            cursor = conn.cursor()
            meta_tb, *_ = manager._l2._get_domain_tables(conn, tenant_id, project_id)

            cursor.execute(
                f"SELECT id FROM {meta_tb} WHERE tenant_id = ? AND project_id = ? AND content = ?",
                (tenant_id, project_id, content),
            )
            row = cursor.fetchone()
            if row:
                return {"status": "redundant", "id": str(row["id"])}

            if subject_hash:
                cursor.execute(
                    f"SELECT id FROM {meta_tb} WHERE tenant_id = ? AND "
                    "project_id = ? AND subject_hash = ? LIMIT 1",
                    (tenant_id, project_id, subject_hash),
                )
                row = cursor.fetchone()
                if row:
                    return {"status": "conflict", "id": str(row["id"])}
        except Exception as exc:  # noqa: BLE001
            logger.warning("CortexMemoryManager: Integrity check failed: %s", exc)
        finally:
            if conn is not None:
                conn.close()
        return {"status": "new", "id": None}

    return await asyncio.to_thread(_sync_check)


def determine_layer(project_id: str, layer: str) -> str:
    """Determine cognitive layer based on project ID semantic rules."""
    project_key = project_id.lower()
    if project_key in ("moskv", "personal", "home", "moskv-1"):
        return "assistant"
    if project_key in ("cortex", "core", "system"):
        return "system"
    return layer if layer else "semantic"


async def emit_to_bus(
    manager: Any,
    fact_id: str,
    tenant_id: str,
    project_id: str,
    content: str,
    fact_type: str,
    layer: str,
    metadata: dict[str, Any] | None,
) -> str:
    """Emit fact record to the experience bus."""
    logger.info("ExperienceBus: Emitting experience:recorded for #%s", fact_id)
    payload = {
        "fact_id": fact_id,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "content": content,
        "fact_type": fact_type,
        "layer": layer,
        "metadata": metadata or {},
    }
    await asyncio.to_thread(
        manager._bus.emit,  # type: ignore[reportOptionalMemberAccess]
        event_type="experience:recorded",
        payload=payload,
        source="memory:manager",
        project=project_id,
    )
    return fact_id


def extract_subject(content: str, metadata: dict[str, Any] | None) -> str:
    """Resolve the subject that participates in conflict detection."""
    if metadata and "subject" in metadata:
        return str(metadata["subject"])
    return content.strip().lower()
