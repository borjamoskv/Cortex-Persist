# [C5-REAL] Exergy-Maximized

import asyncio
import logging
import time
import uuid
from typing import Any

from cortex.memory.engrams import CortexSemanticEngram

logger = logging.getLogger("cortex.memory._manager_store")


async def check_deduplication(l2: Any, tenant_id: str, project_id: str, content: str) -> str | None:
    """Return deduplicated ID if fact exists, else None (async)."""
    if not content or not content.strip():
        logger.warning("CortexMemoryManager: Rejected empty fact pipeline.")
        return "empty"

    if l2 and hasattr(l2, "_get_conn"):

        def _sync_dedup():
            try:
                conn = l2._get_conn()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM facts_meta WHERE tenant_id = ? AND "
                    "project_id = ? AND content = ?",
                    (tenant_id, project_id, content),
                )
                row = cursor.fetchone()
                conn.rollback()
                if row:
                    return str(row["id"])
            except (OSError, RuntimeError, ValueError) as e:
                logger.warning("CortexMemoryManager: Deduplication check failed: %s", e)
            return None

        dedup_id = await asyncio.to_thread(_sync_dedup)
        if dedup_id:
            logger.info("CortexMemoryManager: Fact deduplicated (exact match).")
            return dedup_id
    return None


async def emit_to_bus(
    bus: Any,
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
        bus.emit,
        event_type="experience:recorded",
        payload=payload,
        source="memory:manager",
        project=project_id,
    )
    return fact_id


async def store_fact(
    manager: Any,
    tenant_id: str,
    project_id: str,
    content: str,
    fact_type: str,
    metadata: dict[str, Any] | None,
    layer: str,
    parent_decision_id: str | int | None,
    use_bus: bool,
) -> str:
    """Directly persist a high-value fact to L2 memory layers."""
    conn = manager._l2._get_conn() if hasattr(manager._l2, "_get_conn") else None

    exergy = await manager._mem0_pipeline.evaluate_exergy(
        {"content": content, "fact_type": fact_type, "metadata": metadata}
    )
    if exergy.score < manager._mem0_pipeline.exergy_threshold:
        logger.info(
            "CortexMemoryManager: Fact rejected by Mem0 exergy gate: %s",
            exergy.score,
        )
        return f"filtered:low_exergy:{exergy.score}"

    should_process, action, _ = await manager.thalamus.filter(
        content=content,
        project_id=project_id,
        tenant_id=tenant_id,
        fact_type=fact_type,
        parent_decision_id=int(parent_decision_id) if parent_decision_id else None,
        conn=conn,
    )
    if not should_process:
        logger.info("CortexMemoryManager: Fact filtered by Thalamus. Action: %s", action)
        try:
            from cortex.routes.notch_ws import notify_notch_pruning

            await notify_notch_pruning()
        except ImportError:
            logger.debug("notch_ws unavailable, skipping notification")
        return f"filtered:{action}"

    dedup_id = await manager._check_deduplication(tenant_id, project_id, content)
    if dedup_id:
        return f"filtered:{dedup_id}" if dedup_id == "empty" else f"deduplicated:{dedup_id}"

    _meta = metadata or {}
    
    # [C5-REAL] Strict Schema Contract (Formal Physical Barrier)
    from cortex.types.models import MetadataSchema
    try:
        validated_meta = MetadataSchema(**_meta).model_dump(exclude_unset=True)
        # Ensure we keep extra fields while conforming to the contract
        _meta.update(validated_meta)
    except Exception as e:
        logger.warning("CortexMemoryManager: Fact rejected due to schema validation failure: %s", e)
        return "filtered:invalid_schema"

    if "confidence_score" not in _meta:
        _meta["confidence_score"] = 0.8

    adjusted_layer = manager._determine_layer(project_id, layer)

    if matched_schema := manager._schema_engine.match_schema(content):
        content = manager._schema_engine.apply_encoding_schema(matched_schema, content)
        _meta.update({"active_schema": matched_schema.name})

    vector = await manager._encoder.encode(content)
    fact_id = str(uuid.uuid4())

    candidate = CortexSemanticEngram(
        id=fact_id,
        tenant_id=tenant_id,
        project_id=project_id,
        content=content,
        embedding=vector,
        timestamp=time.time(),
        metadata=_meta,
        cognitive_layer=adjusted_layer,  # type: ignore[reportArgumentType]
        parent_decision_id=int(parent_decision_id) if parent_decision_id is not None else None,
    )

    if manager._resonance_gate is None:
        raise RuntimeError("Resonance gate unavailable; refusing to persist without validation")

    status, engram = await manager._resonance_gate.gate(
        candidate=candidate, precision_mode=(fact_type in ("decision", "rule"))
    )

    if status == "resonance":
        logger.info("CortexMemoryManager: Fact assimilated via resonance with #%s", engram.id)
        return f"deduplicated:{engram.id}"

    if use_bus and manager._bus:
        return await emit_to_bus(
            manager._bus,
            fact_id,
            tenant_id,
            project_id,
            content,
            fact_type,
            adjusted_layer,
            metadata,
        )

    if manager._hdc:
        await manager._hdc.memorize(engram, fact_type=fact_type)

    return engram.id
