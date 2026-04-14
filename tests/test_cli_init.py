from __future__ import annotations

import asyncio
import os

from click.testing import CliRunner

from cortex.cli import cli


class _DummyEngine:
    def __init__(self) -> None:
        self._db_path = "/tmp/test-cortex.db"
        self.no_embed_during_store: list[str | None] = []
        self.closed = False

    async def init_db(self) -> None:
        return None

    async def store(self, **_: object) -> int:
        self.no_embed_during_store.append(os.environ.get("CORTEX_NO_EMBED"))
        return 1

    async def close(self) -> None:
        self.closed = True


def _run(coro):
    return asyncio.run(coro)


def test_init_uses_no_embed_during_seed_and_restores_env(monkeypatch) -> None:
    engine = _DummyEngine()
    runner = CliRunner()

    monkeypatch.setattr("cortex.cli.init_cmds.get_engine", lambda _db: engine)
    monkeypatch.setattr("cortex.cli.init_cmds._run_async", _run)
    monkeypatch.delenv("CORTEX_NO_EMBED", raising=False)

    result = runner.invoke(cli, ["init", "--db", "/tmp/test-cortex.db"])

    assert result.exit_code == 0
    assert engine.no_embed_during_store == ["1"] * 10
    assert os.environ.get("CORTEX_NO_EMBED") is None
    assert engine.closed is True


def test_init_restores_existing_no_embed_value(monkeypatch) -> None:
    engine = _DummyEngine()
    runner = CliRunner()

    monkeypatch.setattr("cortex.cli.init_cmds.get_engine", lambda _db: engine)
    monkeypatch.setattr("cortex.cli.init_cmds._run_async", _run)
    monkeypatch.setenv("CORTEX_NO_EMBED", "0")

    result = runner.invoke(cli, ["init", "--db", "/tmp/test-cortex.db"])

    assert result.exit_code == 0
    assert engine.no_embed_during_store == ["1"] * 10
    assert os.environ.get("CORTEX_NO_EMBED") == "0"
