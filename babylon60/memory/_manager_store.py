# [C5-REAL] Exergy-Maximized

import asyncio
import logging
import time
import uuid
from collections.abc import Mapping
from typing import Any

from babylon60.memory.engrams import CortexSemanticEngram

logger = logging.getLogger("babylon60.memory._manager_store")


async def check_deduplication(l2: Any, tenant_id: str, project_id: str, content: str, vector: list[float] | None = None) -> str | None:
    """Return deduplicated ID if fact exists (exact or semantic), else None (async)."""
    if not content or not content.strip():
        logger.warning("CortexMemoryManager: Rejected empty fact pipeline.")
        return "empty"

    if l2 and hasattr(l2, "_get_conn"):

        def _sync_dedup():
            try:
                conn = l2._get_conn()
                cursor = conn.cursor()
                # 1. Exact string match check
                cursor.execute(
                    "SELECT id FROM facts_meta WHERE tenant_id = ? AND "
                    "project_id = ? AND content = ?",
                    (tenant_id, project_id, content),
                )
                row = cursor.fetchone()
                if row:
                    conn.rollback()
                    return str(row["id"])
                    
                # 2. Semantic vector deduplication (>90% similarity -> cosine distance < 0.10)
                if vector:
                    import numpy as np

                    from babylon60.utils.turboquant import encode_query_qjl
                    
                    rotated_query = encode_query_qjl(vector)
                    embedding_bytes = np.array(rotated_query, dtype=np.float32).tobytes()
                    
                    cursor.execute(
                        "SELECT m.id, v.distance "
                        "FROM vec_facts v "
                        "JOIN facts_meta m ON m.rowid = v.rowid "
                        "WHERE v.embedding MATCH ? AND k = 3 "
                        "AND m.tenant_id = ? AND (m.project_id = ? OR m.is_bridge = 1) "
                        "ORDER BY v.distance ASC LIMIT 1",
                        (embedding_bytes, tenant_id, project_id)
                    )
                    semantic_row = cursor.fetchone()
                    if semantic_row and semantic_row["distance"] < 0.10:
                        logger.info(f"CortexMemoryManager: Fact deduplicated via Semantic Similarity (distance={semantic_row['distance']:.3f}).")
                        conn.rollback()
                        return str(semantic_row["id"])
                        
                conn.rollback()
            except (OSError, RuntimeError, ValueError) as e:
                logger.warning("CortexMemoryManager: Deduplication check failed: %s", e)
            return None

        dedup_id = await asyncio.to_thread(_sync_dedup)
        if dedup_id:
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
    metadata: Mapping[str, Any] | None,
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
        "metadata": dict(metadata) if metadata else {},
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
    metadata: Mapping[str, Any] | None,
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
            from babylon60.routes.notch_ws import notify_notch_pruning

            await notify_notch_pruning()
        except ImportError:
            logger.debug("notch_ws unavailable, skipping notification")
        return f"filtered:{action}"

    dedup_id = await manager._check_deduplication(tenant_id, project_id, content)
    if dedup_id:
        return f"filtered:{dedup_id}" if dedup_id == "empty" else f"deduplicated:{dedup_id}"

    _meta = dict(metadata) if metadata else {}

    # Ouroboros C5-REAL Guard: Taint Provenance Injection at the Edge
    if "CORTEX-TAINT" not in _meta and "cortex_taint" not in _meta:
        try:
            from babylon60.crypto.keys import KeyManager
            from babylon60.engine.causal.taint_engine import generate_secure_taint_token

            km = KeyManager("cortex_persist_enterprise")
            actor_id = tenant_id if tenant_id and tenant_id != "default" else "system"
            
            priv_key = km.get_private_key_b64(actor_id)
            if not priv_key:
                km.generate_and_store_key(actor_id)
                priv_key = km.get_private_key_b64(actor_id)
                
            if priv_key:
                taint_sig = generate_secure_taint_token(
                    agent_id=actor_id,
                    session_id=str(parent_decision_id) if parent_decision_id else "genesis",
                    content=content,
                    private_key_b64=priv_key,
                )
                _meta["CORTEX-TAINT"] = taint_sig
            else:
                logger.warning("C5-REAL: Could not retrieve key for %s, SAGA-2 might abort.", actor_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("C5-REAL: Failed to inject CORTEX-TAINT at the edge: %s", e)

    adjusted_layer = manager._determine_layer(project_id, layer)

    if matched_schema := manager._schema_engine.match_schema(content):
        content = manager._schema_engine.apply_encoding_schema(matched_schema, content)
        _meta.update({"active_schema": matched_schema.name})

    vector = await manager._encoder.encode(content)
    
    # Ouroboros Anti-Rot: Semantic Deduplication
    dedup_id_semantic = await manager._check_deduplication(tenant_id, project_id, content, vector=vector)
    if dedup_id_semantic:
        return f"deduplicated_semantic:{dedup_id_semantic}"

    fact_id = str(uuid.uuid4())

    try:

        confidence = _meta.get("confidence_score") or _meta.get("confidence")
        if not confidence:
            raise ValueError("C5-REAL Guard: confidence_score OBLIGATORIO faltante en payload")
            
        source_meta = _meta.get("source_metadata", _meta.get("provenance"))
        if not source_meta:
            raise ValueError("C5-REAL Guard: provenance/source_metadata OBLIGATORIO faltante en payload")

        # Zero-Knowledge Encryption
        from babylon60.crypto import get_default_encrypter
        enc = get_default_encrypter()
        encrypted_content = enc.encrypt_str(content, tenant_id=tenant_id)
        if not encrypted_content:
            raise ValueError("C5-REAL Guard: Fallo de encriptación Zero-Knowledge")

        candidate = CortexSemanticEngram(
            id=fact_id,
            tenant_id=tenant_id,
            project_id=project_id,
            content=encrypted_content,
            embedding=vector,
            timestamp=time.time(),
            metadata=_meta,
            cognitive_layer=adjusted_layer,  # type: ignore[reportArgumentType]
            parent_decision_id=int(parent_decision_id) if parent_decision_id is not None else None,
            confidence=str(confidence),
            source_metadata=source_meta,
        )
    except (Exception) as e:  # noqa: BLE001
        logger.error("SAGA-1 Abort: Fact validation failed: %s", e)
        return "aborted:validation_error"


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
