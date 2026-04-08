from __future__ import annotations

from cortex.engine.models import Fact


def test_fact_supports_legacy_mapping_access() -> None:
    fact = Fact(
        id=7,
        tenant_id="tenant-a",
        project="alpha",
        content="signal",
        fact_type="knowledge",
        tags=["x"],
        created_at="2026-04-08T00:00:00+00:00",
        updated_at="2026-04-08T00:00:00+00:00",
        confidence="C4",
    )

    assert fact["id"] == 7
    assert fact.get("project") == "alpha"
    assert fact.get("missing", "fallback") == "fallback"
    assert "tenant_id" in fact
