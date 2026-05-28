from __future__ import annotations

import pytest
from fastapi import FastAPI

import cortex.api.core as api_core


@pytest.mark.asyncio
async def test_experimental_daemons_not_started_by_default(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CORTEX_ENABLE_KNOWLEDGE_DAEMON", raising=False)
    monkeypatch.delenv("CORTEX_ENABLE_SWARM", raising=False)
    monkeypatch.setattr(api_core.config, "DB_PATH", str(tmp_path / "api.db"))

    app = FastAPI()
    async with api_core.lifespan(app):
        assert app.state.watcher is None
        assert app.state.swarm_daemon is None
