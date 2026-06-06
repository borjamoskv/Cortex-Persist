# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("cortex.engine.validation")


async def _check_byzantine_auth(
    mixin_instance: Any, meta: dict | None, source: str | None, tenant_id: str
) -> None:
    """Validate OS_COMMAND intent via Byzantine consensus if required."""
    if meta and meta.get("intent") == "OS_COMMAND":
        auth = getattr(mixin_instance, "auth", None)
        if auth:
            actor = source or tenant_id or "unknown_agent"
            success = await auth.acquire_lock("OS_COMMAND", actor)
            if not success:
                logger.error("🛑 [BYZANTINE-AUTH] Permission DENIED for OS_COMMAND.")
                raise PermissionError("OS_COMMAND blocked: Byzantine consensus failed.")


def _enforce_thermodynamics(cls: Any, fact_type: str, skip_thermo: bool) -> None:
    """Enforce Axiom Ω₁₃ (Landauer Limit) for active vs decorative modes."""
    from cortex.guards.thermodynamic import AgentMode

    if (
        cls._agent_mode == AgentMode.DECORATIVE
        and fact_type not in ("error", "ghost")
        and not skip_thermo
    ):
        logger.warning("🚫 [DECORATIVE MODE] Write blocked for type: %s", fact_type)
        raise RuntimeError("Operation blocked: Agent in DECORATIVE mode (Axiom Ω₁₃)")


async def _apply_semantic_dedup(
    mixin_instance: Any,
    conn: Any,
    project: str,
    content: str,
    tenant_id: str,
) -> int | None:
    """Perform semantic recall to detect thermal decay loops or near-duplicates."""
    manager = getattr(mixin_instance, "_memory_manager", None)
    if not (manager and getattr(manager, "_l2", None)):
        return None

    try:
        similar = await manager._l2.recall(
            query=content, limit=1, project=project, tenant_id=tenant_id
        )
        if not similar:
            return None

        top = similar[0]
        if getattr(top, "_recall_score", 0.0) > 0.92:
            cls = mixin_instance.__class__
            fid = int(top.id)
            hits = cls._thermal_decay_cache.get(fid, 0) + 1
            cls._thermal_decay_cache[fid] = hits

            if hits > 4:
                await mixin_instance.deprecate(fid, f"Thermal decay ({hits}x)", conn, tenant_id)
                cls._thermal_decay_cache[fid] = 0
            else:
                try:
                    await conn.execute(
                        "UPDATE facts SET last_accessed = CURRENT_TIMESTAMP WHERE id=?", (fid,)
                    )
                except Exception as e:
                    logger.debug("Skipping last_accessed update for fact %s: %s", fid, e)
            return fid
    except Exception as e:
        logger.debug("Semantic dedup skipped: %s", e)
    return None


async def _enforce_ctre(meta: dict | None) -> None:
    """Enforce Commit-Time Reconciliation Engine (CTRE) logic for UI_ACTION."""
    if meta and meta.get("intent") == "UI_ACTION" and "expected_ui_hash" in meta:
        from cortex.guards.ctre_guard import CTRECollisionError, CTREGuard

        expected_hash = meta["expected_ui_hash"]
        current_hash = meta.get("current_ui_hash", expected_hash)
        target_x = meta.get("ui_target_x", 0.0)
        target_y = meta.get("ui_target_y", 0.0)

        success, epsilon = CTREGuard.validate_commit(
            expected_hash=expected_hash,
            current_hash=current_hash,
            target_x=target_x,
            target_y=target_y,
        )
        if not success:
            logger.error(
                f"🛑 [CTRE] SAGA ABORT: UI TOCTOU Collision detected. Epsilon: {epsilon}µs"
            )
            raise CTRECollisionError(expected_hash, current_hash, epsilon)


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
    """Orchestrates the multi-stage validation pipeline for memory storage."""
    _validate_dependencies()
    await _check_byzantine_auth(mixin_instance, meta, source, tenant_id)
    await _enforce_ctre(meta)

    cls = mixin_instance.__class__
    skip_thermo = os.getenv("CORTEX_SKIP_EXERGY_VALIDATION") == "1"
    _enforce_thermodynamics(cls, fact_type, skip_thermo)
    _apply_exergy(cls, meta, fact_type, skip_thermo)

    from cortex.engine.storage_guard import StorageGuard
    from cortex.engine.store_validators import check_dedup, validate_content

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
        if (eid := await check_dedup(conn, tenant_id, project, content)) is not None:
            return eid, meta, content, fact_type
        if fid := await _apply_semantic_dedup(mixin_instance, conn, project, content, tenant_id):
            return fid, meta, content, fact_type

    meta = mixin_instance._apply_privacy_shield(content, project, meta)
    content, meta = _sanitize_engram(content, fact_type, source, project, meta)

    from cortex.engine.fact_store_core import resolve_causality_async

    meta = await resolve_causality_async(conn, project, meta)

    nemesis_rejection = None
    if fact_type not in ("error", "ghost"):
        from cortex.engine.nemesis import NemesisProtocol

        nemesis_rejection = await NemesisProtocol.analyze_async(content, conn=conn)

    bridge_result = None
    if fact_type not in ("error", "ghost") and not (meta and meta.get("previous_fact_id")):
        content, fact_type, bridge_result = await _apply_bridge_guard(
            conn, content, project, tenant_id, fact_type
        )
        if bridge_result and bridge_result.get("meta_flags"):
            meta = {**(meta or {}), **bridge_result["meta_flags"]}

    from cortex.engine.guard_integration_patch import enforce_store_guards

    await enforce_store_guards(
        content=content,
        project=project,
        tenant_id=tenant_id,
        fact_type=fact_type,
        meta=meta or {},
        nemesis_rejection=nemesis_rejection,
        bridge_result=bridge_result,
    )

    await _enforce_cortex_taint(conn, content, fact_type, meta)

    return None, meta, content, fact_type


def _validate_dependencies():
    try:
        from cortex.engine.bridge_guard import BridgeGuard  # noqa
        from cortex.engine.guard_integration_patch import enforce_store_guards  # noqa
        from cortex.engine.membrane.sanitizer import SovereignSanitizer  # noqa
        from cortex.engine.nemesis import NemesisProtocol  # noqa
        from cortex.engine.storage_guard import StorageGuard  # noqa
        from cortex.guards.thermodynamic import AgentMode, should_enter_decorative_mode  # noqa
        from cortex.shannon.exergy import ActionRisk, ExergyInput, calculate_exergy, enforce_exergy  # noqa
    except Exception as exc:
        raise RuntimeError(f"FAIL-CLOSED: dependencies unavailable: {exc}") from exc


def _apply_exergy(cls: Any, meta: dict[str, Any] | None, fact_type: str, skip_thermo: bool):
    from cortex.guards.thermodynamic import AgentMode, should_enter_decorative_mode
    from cortex.shannon.exergy import ActionRisk, ExergyInput, calculate_exergy, enforce_exergy

    _has_entropy = meta is not None and ("_prior_entropy" in meta or "_posterior_entropy" in meta)
    if not skip_thermo and meta is not None and _has_entropy:
        ex_input = ExergyInput(
            prior_uncertainty=meta.get("_prior_entropy", 1.0),
            posterior_uncertainty=meta.get("_posterior_entropy", 0.5),
            tokens_consumed=meta.get("_tokens", 100),
            action_risk=ActionRisk.MEMORY_WRITE
            if fact_type != "rule"
            else ActionRisk.SCHEMA_MUTATION,
            had_backup=True,
            touched_persistent_state=True,
            utility_delta=meta.get("_utility", 0.0),
            causal_gap=meta.get("_causal_gap", 0.0),
        )
        ex_res = calculate_exergy(ex_input, threshold_min_work=0.01)
        enforce_exergy(ex_res)
        meta["_exergy_score"] = ex_res.exergy_score
        if should_enter_decorative_mode(cls._thermo_counters)[0]:
            cls._agent_mode = AgentMode.DECORATIVE
            logger.error("🛑 [CRITICAL] Agent entering DECORATIVE mode (Ω₁₃).")
    elif cls._agent_mode != AgentMode.DECORATIVE:
        cls._agent_mode = AgentMode.ACTIVE


def _sanitize_engram(
    content: str, fact_type: str, source: str | None, project: str, meta: dict | None
):
    from cortex.engine.membrane.sanitizer import SovereignSanitizer

    raw_engram = {
        "type": fact_type,
        "source": source or "engine:store",
        "topic": project,
        "content": content,
        "metadata": meta or {},
    }
    pure, membrane_log = SovereignSanitizer.digest(raw_engram)
    m = pure.metadata
    m["_membrane_log"] = (
        membrane_log.model_dump() if hasattr(membrane_log, "model_dump") else membrane_log.dict()
    )
    return pure.content, m


async def _enforce_cortex_taint(
    conn: Any,
    content: str,
    fact_type: str,
    meta: dict[str, Any] | None,
) -> None:
    """Enforce attribution before ledger or persistence mutation begins."""
    if fact_type in ("telemetry_batch", "mafia_node"):
        return
    from cortex.engine.causal.taint_engine import enforce_taint_check

    token = meta.get("cortex_taint") if meta else None
    await enforce_taint_check(conn, token, content)


async def _apply_bridge_guard(conn, content, project, tenant_id, fact_type):
    from cortex.engine.bridge_guard import BridgeGuard

    source_proj = await BridgeGuard.detect_bridge_candidate(conn, content, project, tenant_id)
    bridge_result = None
    if source_proj:
        fact_type = "bridge"
        if "→" not in content and "->" not in content:
            content = f"Pattern from {source_proj} → {project}. Adaptation: {content}"
        bridge_result = await BridgeGuard.validate_bridge(conn, content, project, tenant_id)
    return content, fact_type, bridge_result
