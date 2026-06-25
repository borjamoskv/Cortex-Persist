# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from types import SimpleNamespace

import pytest

from legacy_research.engine import store_validation as sv


@pytest.mark.asyncio
async def test_taint_is_verified_after_bridge_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    async def noop_async(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(sv, "_validate_dependencies", lambda: None)
    monkeypatch.setattr(sv, "_check_byzantine_auth", noop_async)
    monkeypatch.setattr(sv, "_enforce_thermodynamics", lambda *args, **kwargs: None)
    monkeypatch.setattr(sv, "_apply_exergy", lambda *args, **kwargs: None)
    monkeypatch.setattr("cortex.engine.storage_guard.StorageGuard.validate", lambda **kwargs: None)
    monkeypatch.setattr("cortex.engine.store_validators.check_dedup", noop_async)
    monkeypatch.setattr(sv, "_apply_semantic_dedup", noop_async)
    monkeypatch.setattr(
        sv,
        "_sanitize_engram",
        lambda content, fact_type, source, project, meta: (content, meta or {}),
    )

    async def bridge_guard(conn, content, project, tenant_id, fact_type):
        return f"bridged::{content}", "bridge", {"meta_flags": {"bridged": True}}

    async def resolve_causality(conn, project, meta):
        return meta or {}

    monkeypatch.setattr(sv, "_apply_bridge_guard", bridge_guard)
    monkeypatch.setattr("cortex.engine.fact_store_core.resolve_causality_async", resolve_causality)
    monkeypatch.setattr("cortex.engine.nemesis.NemesisProtocol.analyze_async", noop_async)
    monkeypatch.setattr("cortex.engine.guard_integration_patch.enforce_store_guards", noop_async)

    async def capture_taint(conn, content, fact_type, meta):
        captured["content"] = content

    monkeypatch.setattr(sv, "_enforce_cortex_taint", capture_taint)

    mixin = SimpleNamespace(_apply_privacy_shield=lambda content, project, meta: meta or {})
    result = await sv.run_store_validation_logic(
        mixin_instance=mixin,
        conn=object(),
        project="alpha",
        content="seed content",
        tenant_id="tenant-a",
        fact_type="knowledge",
        tags=[],
        confidence="stated",
        source="agent:test",
        meta={"cortex_taint": "taint:agent:session:2026-06-06T00:00:00+00:00:nonce:sig"},
    )

    assert captured["content"] == "bridged::seed content"
    assert result[2] == "bridged::seed content"
