def test_registry_records_snapshot(registry):
    snap = registry.record_snapshot("AGENTS", {"c": 1})
    assert snap.snapshot_id is not None
    assert snap.prev_hash is None

def test_registry_chain_links(registry):
    s1 = registry.record_snapshot("AGENTS_1", {})
    s2 = registry.record_snapshot("AGENTS_2", {})
    assert s2.prev_hash == s1.snapshot_id

def test_current_snapshot_returns_latest(registry):
    assert registry.current_snapshot() is None
    registry.record_snapshot("AGENTS", {})
    assert registry.current_snapshot() is not None

def test_registry_handler_registration(registry):
    handler = lambda x: x * 2
    registry.register_handler("double", handler)
    assert registry.get_handler("double") == handler

def test_registry_duplicate_handler_raises_exception(registry):
    import pytest
    handler1 = lambda x: x * 2
    handler2 = lambda x: x * 3
    registry.register_handler("op", handler1)
    with pytest.raises(ValueError, match="Handler 'op' already registered"):
        registry.register_handler("op", handler2)

def test_registry_load_agents_md(registry, tmp_path):
    p = tmp_path / "AGENTS.md"
    content = "# Test content"
    p.write_text(content, encoding="utf-8")
    assert registry.load_agents_md(p) == content

