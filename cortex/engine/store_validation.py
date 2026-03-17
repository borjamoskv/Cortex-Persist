"""Logic for store validation and thermodynamic enforcement."""

from __future__ import annotations

import logging
from typing import Any

from cortex.engine.bridge_guard import BridgeGuard
from cortex.engine.membrane.sanitizer import SovereignSanitizer
from cortex.engine.nemesis import NemesisProtocol
from cortex.engine.storage_guard import StorageGuard
from cortex.engine.store_validators import check_dedup, validate_content
from cortex.guards.thermodynamic import AgentMode, should_enter_decorative_mode
from cortex.shannon.exergy import ActionRisk, ExergyInput, calculate_exergy, enforce_exergy

logger = logging.getLogger("cortex.engine.validation")


async def run_store_validation_logic(
    mixin_instance: Any,
    conn: Any,
    project: str,
    content: str,
    tenant_id: str,
    fact_type: str,
    tags: list[str] | None,
    confidence: str,
    source: str | None,
    meta: dict[str, Any] | None,
) -> tuple[int | None, dict[str, Any] | None, str, str]:
    """Extracted validation logic from StoreMixin."""
    cls = mixin_instance.__class__

    import os

    skip_thermo = os.getenv("CORTEX_SKIP_EXERGY_VALIDATION")

    # ═══ Axiom Ω₁₃: Thermodynamic Enforcement ═══
    if (
        cls._agent_mode == AgentMode.DECORATIVE
        and fact_type not in ("error", "ghost")
        and not skip_thermo
    ):
        logger.warning("🚫 [DECORATIVE MODE] Write blocked for type: %s", fact_type)
        raise RuntimeError("Operation blocked: Agent in DECORATIVE mode (Axiom Ω₁₃)")

    # Exergy validation: only enforce when caller provides explicit entropy
    # metadata (programmatic/agent path). CLI stores without _prior_entropy
    # are human-intentional and bypass the thermodynamic gate.
    _has_entropy_meta = meta and ("_prior_entropy" in meta or "_posterior_entropy" in meta)
    if not skip_thermo and _has_entropy_meta:
        ex_input = ExergyInput(
            prior_uncertainty=meta.get("_prior_entropy", 1.0),
            posterior_uncertainty=meta.get("_posterior_entropy", 0.5),
            tokens_consumed=meta.get("_tokens", 100),
            action_risk=ActionRisk.MEMORY_WRITE
            if fact_type != "rule"
            else ActionRisk.SCHEMA_MUTATION,
            had_backup=True,
            touched_persistent_state=True,
        )
        ex_res = calculate_exergy(ex_input, threshold_min_work=0.01)
        enforce_exergy(ex_res)

        if should_enter_decorative_mode(cls._thermo_counters):
            cls._agent_mode = AgentMode.DECORATIVE
            logger.error("🛑 [CRITICAL] Agent entering DECORATIVE mode due to thermodynamic waste.")
    else:
        # Ensure we stay in ACTIVE mode during tests
        cls._agent_mode = AgentMode.ACTIVE

    StorageGuard.validate(
        project=project,
        content=content,
        fact_type=fact_type,
        source=source,
        confidence=confidence,
        tags=tags,
        meta=meta,
    )
    content = validate_content(project, content, fact_type)

    if not (meta and meta.get("previous_fact_id")):
        if (existing_id := await check_dedup(conn, tenant_id, project, content)) is not None:
            return existing_id, meta, content, fact_type

        manager = getattr(mixin_instance, "_memory_manager", None)
        if manager is not None and getattr(manager, "_l2", None) is not None:
            try:
                similar_facts = await manager._l2.recall(
                    query=content, limit=1, project=project, tenant_id=tenant_id
                )
                if similar_facts:
                    top_match = similar_facts[0]
                    score = getattr(top_match, "_recall_score", 0.0)
                    if score > 0.92:
                        fact_id_int = int(top_match.id)
                        hits = cls._thermal_decay_cache.get(fact_id_int, 0) + 1
                        cls._thermal_decay_cache[fact_id_int] = hits

                        if hits > 4:
                            await mixin_instance.deprecate(
                                fact_id=fact_id_int,
                                reason=f"Thermal decay (loop {hits}x)",
                                conn=conn,
                                tenant_id=tenant_id,
                            )
                            cls._thermal_decay_cache[fact_id_int] = 0
                        else:
                            await conn.execute(
                                "UPDATE facts SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                                (fact_id_int,),
                            )
                        return fact_id_int, meta, content, fact_type
            except Exception as e:
                logger.debug("Semantic dedup skipped: %s", e)

    meta = mixin_instance._apply_privacy_shield(content, project, meta)
    from cortex.engine.store_guards import run_security_guards

    meta = run_security_guards(content, project, source, meta)

    raw_engram = {
        "type": fact_type,
        "source": source or "engine:store",
        "topic": project,
        "content": content,
        "metadata": meta or {},
    }
    pure_engram, membrane_log = SovereignSanitizer.digest(raw_engram)
    content, meta = pure_engram.content, pure_engram.metadata
    if hasattr(membrane_log, "model_dump"):
        meta["_membrane_log"] = membrane_log.model_dump()
    else:
        meta["_membrane_log"] = membrane_log.dict()

    from cortex.engine.fact_store_core import resolve_causality_async

    meta = await resolve_causality_async(conn, project, meta)

    if fact_type not in ("error", "ghost"):
        if rej := await NemesisProtocol.analyze_async(content, conn=conn):
            raise ValueError(rej)

    if fact_type in ("knowledge", "decision", "rule", "ghost") and not (
        meta and meta.get("previous_fact_id")
    ):
        source_proj = await BridgeGuard.detect_bridge_candidate(conn, content, project, tenant_id)
        if source_proj:
            fact_type = "bridge"
            if "→" not in content and "->" not in content:
                content = f"Pattern from {source_proj} → {project}. Adaptation: {content}"

    if fact_type == "bridge":
        bridge_res = await BridgeGuard.validate_bridge(conn, content, project, tenant_id)
        if not bridge_res["allowed"]:
            raise ValueError(f"BRIDGE BLOCKED: {bridge_res['reason']}")
        if bridge_res["meta_flags"]:
            meta = {**(meta or {}), **bridge_res["meta_flags"]}

    return None, meta, content, fact_type
