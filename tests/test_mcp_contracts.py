from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("mcp.server.fastmcp")

from cortex.extensions.immune.filters.base import Verdict
from cortex.mcp import server as mcp_server


class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class _FakeMetrics:
    def record_error(self, is_immune_rejection: bool = False) -> None:
        pass

    def record_request(self, cached: bool = False) -> None:
        pass

    def get_summary(self) -> dict[str, int]:
        return {"requests": 0, "errors": 0}


class _FakeCache:
    def __init__(self) -> None:
        self.keys: list[str] = []

    def get(self, key: str) -> None:
        self.keys.append(key)
        return None

    def set(self, key: str, value: str) -> None:
        self.keys.append(key)

    def clear(self) -> None:
        pass


class _FakeMembrane:
    async def intercept(self, *_args, **_kwargs):
        return SimpleNamespace(verdict=Verdict.PASS, risks_assumed=[])


class _Acquire:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *args):
        return None


class _FakePool:
    def acquire(self):
        return _Acquire()


class _FakeContext:
    def __init__(self) -> None:
        self.cfg = SimpleNamespace(db_path=":memory:")
        self.metrics = _FakeMetrics()
        self.pool = _FakePool()
        self.search_cache = _FakeCache()
        self.membrane = _FakeMembrane()

    async def ensure_ready(self) -> None:
        pass


@pytest.mark.asyncio
async def test_mcp_store_calls_engine_store_with_keywords(monkeypatch) -> None:
    observed: dict[str, Any] = {}

    class FakeEngine:
        def __init__(self, *args, **kwargs) -> None:
            self._conn = None

        async def store(self, **kwargs):
            observed.update(kwargs)
            return 42

    monkeypatch.setattr(mcp_server, "CortexEngine", FakeEngine)
    fake_mcp = _FakeMCP()
    mcp_server._register_store_tool(fake_mcp, _FakeContext())

    result = await fake_mcp.tools["cortex_store"](
        project="alpha",
        content="stored content",
        tenant_id="tenant-a",
        fact_type="decision",
        tags='["audit"]',
        source="agent",
        parent_decision_id=7,
        meta='{"priority":"high"}',
    )

    assert "Stored fact #42" in result
    assert observed == {
        "project": "alpha",
        "content": "stored content",
        "tenant_id": "tenant-a",
        "fact_type": "decision",
        "tags": ["audit"],
        "confidence": "stated",
        "source": "agent",
        "parent_decision_id": 7,
        "meta": {"priority": "high"},
    }


@pytest.mark.asyncio
async def test_mcp_search_calls_engine_search_with_keywords_and_tenant_cache(monkeypatch) -> None:
    observed: dict[str, Any] = {}

    class FakeEngine:
        def __init__(self, *args, **kwargs) -> None:
            self._conn = None

        async def search(self, **kwargs):
            observed.update(kwargs)
            return [
                SimpleNamespace(
                    fact_id=3,
                    score=0.9,
                    project="alpha",
                    fact_type="knowledge",
                    content="search hit",
                )
            ]

    ctx = _FakeContext()
    monkeypatch.setattr(mcp_server, "CortexEngine", FakeEngine)
    fake_mcp = _FakeMCP()
    mcp_server._register_search_tool(fake_mcp, ctx)

    output = await fake_mcp.tools["cortex_search"](
        query="hit",
        tenant_id="tenant-a",
        project="alpha",
        top_k=50,
    )

    assert "search hit" in output
    assert observed == {
        "query": "hit",
        "tenant_id": "tenant-a",
        "project": "alpha",
        "top_k": 20,
    }
    assert any(key.startswith("tenant-a:hit:alpha:50") for key in ctx.search_cache.keys)


@pytest.mark.asyncio
async def test_mcp_ledger_verify_accepts_tx_count_report(monkeypatch) -> None:
    class FakeLedger:
        def __init__(self, pool) -> None:
            self.pool = pool

        async def audit_integrity_async(self, tenant_id: str = "default"):
            return {"valid": True, "violations": [], "tx_count": 9}

    monkeypatch.setattr(mcp_server, "ImmutableLedger", FakeLedger)
    fake_mcp = _FakeMCP()
    mcp_server._register_ledger_tool(fake_mcp, _FakeContext())

    output = await fake_mcp.tools["cortex_ledger_verify"](tenant_id="tenant-a")

    assert "Ledger Integrity: OK" in output
    assert "Transactions verified: 9" in output
    assert "Violations: 0" in output


@pytest.mark.asyncio
async def test_mcp_status_passes_tenant_id(monkeypatch) -> None:
    observed: dict[str, Any] = {}

    class FakeEngine:
        def __init__(self, *args, **kwargs) -> None:
            self._conn = None

        async def stats(self, tenant_id: str = "default"):
            observed["tenant_id"] = tenant_id
            return {"total_facts": 1, "active_facts": 1, "project_count": 1, "types": {}}

    monkeypatch.setattr(mcp_server, "CortexEngine", FakeEngine)
    fake_mcp = _FakeMCP()
    mcp_server._register_status_tool(fake_mcp, _FakeContext())

    output = await fake_mcp.tools["cortex_status"](tenant_id="tenant-a")

    assert "Tenant: tenant-a" in output
    assert observed == {"tenant_id": "tenant-a"}


def test_create_mcp_server_registers_core_tools(monkeypatch) -> None:
    class FakeFastMCP(_FakeMCP):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__()

    monkeypatch.setattr(mcp_server, "_MCP_AVAILABLE", True)
    monkeypatch.setattr(mcp_server, "FastMCP", FakeFastMCP)

    monkeypatch.setattr(mcp_server, "_register_trace_episode_tool", lambda mcp, ctx: None)
    monkeypatch.setattr(mcp_server, "_register_trace_chain_tool", lambda mcp, ctx: None)
    monkeypatch.setattr(mcp_server, "_register_shannon_report_tool", lambda mcp, ctx: None)
    monkeypatch.setattr(mcp_server, "_register_handoff_tool", lambda mcp, ctx: None)
    monkeypatch.setattr(mcp_server, "_register_embed_tool", lambda mcp, ctx: None)
    monkeypatch.setattr(mcp_server, "_register_embed_status_tool", lambda mcp, ctx: None)
    monkeypatch.setattr(mcp_server, "register_trust_tools", lambda mcp, ctx: None)
    monkeypatch.setattr(mcp_server, "register_mega_tools", lambda mcp, ctx: None)
    monkeypatch.setattr(mcp_server, "register_genesis_tools", lambda mcp, ctx: None)
    monkeypatch.setattr(mcp_server, "register_health_tools", lambda mcp, ctx: None)
    monkeypatch.setattr(mcp_server, "register_singularity_tools", lambda mcp: None)
    monkeypatch.setattr(mcp_server, "_register_optional_music_tools", lambda mcp: None)
    monkeypatch.setattr(mcp_server, "register_hilbert_tools", lambda mcp: None, raising=False)

    import sys
    import types

    hilbert = types.ModuleType("cortex.mcp.hilbert_tools")
    hilbert.register_hilbert_tools = lambda mcp, ctx: None
    monkeypatch.setitem(sys.modules, "cortex.mcp.hilbert_tools", hilbert)

    server = mcp_server.create_mcp_server(mcp_server.MCPServerConfig())

    assert isinstance(server, FakeFastMCP)
    assert {"cortex_store", "cortex_search", "cortex_status", "cortex_ledger_verify"} <= set(
        server.tools
    )


def test_mcp_run_server_daemons_are_opt_in(monkeypatch) -> None:
    calls: list[str] = []

    knowledge_module = types.ModuleType("cortex.mcp.knowledge_watcher")
    knowledge_module.start_knowledge_daemon = lambda: calls.append("knowledge")
    swarm_module = types.ModuleType("cortex.swarm")
    swarm_module.start_swarm_daemon = lambda: calls.append("swarm")

    monkeypatch.setitem(sys.modules, "cortex.mcp.knowledge_watcher", knowledge_module)
    monkeypatch.setitem(sys.modules, "cortex.swarm", swarm_module)
    monkeypatch.delenv("CORTEX_ENABLE_KNOWLEDGE_DAEMON", raising=False)
    monkeypatch.delenv("CORTEX_ENABLE_SWARM", raising=False)
    monkeypatch.setattr(mcp_server, "mcp", SimpleNamespace(run=lambda **_kwargs: calls.append("run")))

    mcp_server.run_server()

    assert calls == ["run"]


def test_mcp_run_server_starts_opt_in_daemons(monkeypatch) -> None:
    calls: list[str] = []

    knowledge_module = types.ModuleType("cortex.mcp.knowledge_watcher")
    knowledge_module.start_knowledge_daemon = lambda: calls.append("knowledge")
    swarm_module = types.ModuleType("cortex.swarm")
    swarm_module.start_swarm_daemon = lambda: calls.append("swarm")

    monkeypatch.setitem(sys.modules, "cortex.mcp.knowledge_watcher", knowledge_module)
    monkeypatch.setitem(sys.modules, "cortex.swarm", swarm_module)
    monkeypatch.setenv("CORTEX_ENABLE_KNOWLEDGE_DAEMON", "1")
    monkeypatch.setenv("CORTEX_ENABLE_SWARM", "true")
    monkeypatch.setattr(mcp_server, "mcp", SimpleNamespace(run=lambda **_kwargs: calls.append("run")))

    mcp_server.run_server()

    assert calls == ["knowledge", "swarm", "run"]
