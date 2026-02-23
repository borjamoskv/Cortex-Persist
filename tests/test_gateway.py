"""CORTEX Gateway — Test suite (HYDRA Test Engineer agent)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.gateway import (
    GatewayIntent,
    GatewayRequest,
    GatewayResponse,
    GatewayRouter,
)


# ─── Fixtures ────────────────────────────────────────────────────────


def make_engine(
    store_id: int = 42,
    search_results: list | None = None,
    recall_results: list | None = None,
    stats: dict | None = None,
) -> MagicMock:
    """Build a mock CortexEngine."""
    engine = MagicMock()
    engine.store = AsyncMock(return_value=store_id)
    engine.search = AsyncMock(return_value=search_results or [])
    engine.recall = AsyncMock(return_value=recall_results or [])
    engine.stats = AsyncMock(return_value=stats or {
        "total_facts": 100,
        "active_facts": 90,
        "project_count": 5,
        "db_size_mb": 1.2,
    })
    return engine


def make_bus() -> MagicMock:
    bus = MagicMock()
    bus.emit = AsyncMock()
    bus.adapter_names = ["telegram", "macos"]
    return bus


def make_req(**kwargs) -> GatewayRequest:
    defaults = dict(
        intent=GatewayIntent.STATUS,
        payload={},
        project="cortex",
        source="test",
    )
    defaults.update(kwargs)
    return GatewayRequest(**defaults)


# ─── GatewayRequest tests ────────────────────────────────────────────


class TestGatewayRequest:
    def test_auto_request_id(self):
        req = make_req()
        assert req.request_id.startswith("gw-")

    def test_defaults(self):
        req = GatewayRequest(intent=GatewayIntent.STATUS)
        assert req.project == ""
        assert req.source == "api"
        assert req.tenant_id == "default"


# ─── GatewayResponse tests ───────────────────────────────────────────


class TestGatewayResponse:
    def test_to_dict(self):
        resp = GatewayResponse(
            ok=True,
            data={"fact_id": 1},
            intent=GatewayIntent.STORE,
            request_id="gw-123",
            latency_ms=12.5,
        )
        d = resp.to_dict()
        assert d["ok"] is True
        assert d["intent"] == "store"
        assert d["latency_ms"] == 12.5


# ─── GatewayRouter tests ─────────────────────────────────────────────


class TestGatewayRouter:
    @pytest.mark.asyncio
    async def test_handle_status(self):
        engine = make_engine()
        router = GatewayRouter(engine=engine)
        resp = await router.handle(make_req(intent=GatewayIntent.STATUS))
        assert resp.ok
        assert resp.data["total_facts"] == 100

    @pytest.mark.asyncio
    async def test_handle_store(self):
        engine = make_engine(store_id=99)
        router = GatewayRouter(engine=engine)
        resp = await router.handle(make_req(
            intent=GatewayIntent.STORE,
            payload={"content": "Decision: use Byzantine", "type": "decision"},
        ))
        assert resp.ok
        assert resp.data["fact_id"] == 99

    @pytest.mark.asyncio
    async def test_handle_store_missing_content(self):
        engine = make_engine()
        router = GatewayRouter(engine=engine)
        resp = await router.handle(make_req(
            intent=GatewayIntent.STORE,
            payload={},  # no content
        ))
        assert not resp.ok
        assert "content" in resp.error

    @pytest.mark.asyncio
    async def test_handle_search(self):
        result = MagicMock()
        result.fact_id = 1
        result.content = "test content"
        result.score = 0.95
        result.project = "cortex"
        result.fact_type = "decision"

        engine = make_engine(search_results=[result])
        router = GatewayRouter(engine=engine)
        resp = await router.handle(make_req(
            intent=GatewayIntent.SEARCH,
            payload={"query": "Byzantine", "top_k": 3},
        ))
        assert resp.ok
        assert len(resp.data) == 1
        assert resp.data[0]["score"] >= 0

    @pytest.mark.asyncio
    async def test_handle_search_missing_query(self):
        engine = make_engine()
        router = GatewayRouter(engine=engine)
        resp = await router.handle(make_req(
            intent=GatewayIntent.SEARCH,
            payload={},
        ))
        assert not resp.ok

    @pytest.mark.asyncio
    async def test_handle_emit_with_bus(self):
        bus = make_bus()
        engine = make_engine()
        router = GatewayRouter(engine=engine, bus=bus)
        resp = await router.handle(make_req(
            intent=GatewayIntent.EMIT,
            payload={"severity": "warning", "title": "Test alert", "body": "from test"},
        ))
        assert resp.ok
        bus.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_emit_without_bus(self):
        engine = make_engine()
        router = GatewayRouter(engine=engine, bus=None)
        resp = await router.handle(make_req(
            intent=GatewayIntent.EMIT,
            payload={"severity": "info", "title": "Test", "body": ""},
        ))
        assert resp.ok
        assert resp.data["delivered"] is False

    @pytest.mark.asyncio
    async def test_unknown_intent_returns_error(self):
        engine = make_engine()
        router = GatewayRouter(engine=engine)

        class FakeIntent:
            value = "unknown_intent"

        req = GatewayRequest.__new__(GatewayRequest)
        req.intent = FakeIntent()
        req.request_id = "gw-test"
        req.payload = {}
        req.project = ""
        req.source = "test"
        req.tenant_id = "default"
        req.caller_id = ""

        resp = await router.handle(req)
        assert not resp.ok

    @pytest.mark.asyncio
    async def test_engine_error_returns_error_response(self):
        engine = make_engine()
        engine.store = AsyncMock(side_effect=RuntimeError("DB exploded"))
        router = GatewayRouter(engine=engine)
        resp = await router.handle(make_req(
            intent=GatewayIntent.STORE,
            payload={"content": "test"},
        ))
        assert not resp.ok
        assert "DB exploded" in resp.error

    @pytest.mark.asyncio
    async def test_latency_is_measured(self):
        engine = make_engine()
        router = GatewayRouter(engine=engine)
        resp = await router.handle(make_req(intent=GatewayIntent.STATUS))
        assert resp.latency_ms >= 0


# ─── Telegram adapter parser tests ───────────────────────────────────


class TestTelegramParser:
    def _parse(self, text):
        from cortex.gateway.adapters.telegram import _parse_telegram_message
        return _parse_telegram_message(text)

    def test_store_command(self):
        req = self._parse("/store cortex This is a decision")
        assert req is not None
        assert req.intent == GatewayIntent.STORE
        assert req.project == "cortex"
        assert "decision" in req.payload["content"]

    def test_search_command(self):
        req = self._parse("/search cortex Byzantine consensus")
        assert req is not None
        assert req.intent == GatewayIntent.SEARCH
        assert "Byzantine" in req.payload["query"]

    def test_status_command(self):
        req = self._parse("/status")
        assert req is not None
        assert req.intent == GatewayIntent.STATUS

    def test_recall_command(self):
        req = self._parse("/recall naroa-2026")
        assert req is not None
        assert req.intent == GatewayIntent.RECALL
        assert req.project == "naroa-2026"

    def test_unknown_command_returns_none(self):
        assert self._parse("/foobar") is None

    def test_non_command_returns_none(self):
        assert self._parse("hello world") is None

    def test_bot_name_stripped(self):
        req = self._parse("/status@CORTEXBot")
        assert req is not None
        assert req.intent == GatewayIntent.STATUS

    def test_emit_command(self):
        req = self._parse("/emit warning Ghost backlog | 30+ ghosts pending")
        assert req is not None
        assert req.intent == GatewayIntent.EMIT
        assert req.payload["severity"] == "warning"
        assert "Ghost backlog" in req.payload["title"]
