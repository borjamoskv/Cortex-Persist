from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from click.testing import CliRunner

from cortex.cli.ledger import ledger_cmds
from cortex.extensions.evolution.agents import Mutation
from cortex.extensions.evolution.operations_mixin import EvolutionOpsMixin


class _DummyEvolutionOps(EvolutionOpsMixin):
    def __init__(self) -> None:
        self._ledger = AsyncMock()


async def test_record_merkle_checkpoint_awaits_ledger_write() -> None:
    ops = _DummyEvolutionOps()
    mutation = Mutation(mutation_id="mut-001", description="checkpoint-worthy")
    agent = SimpleNamespace(
        id="agent-omega",
        state_hash="state-hash-123",
        generation=7,
        mutations=[mutation],
    )

    await ops._record_merkle_checkpoint(agent, mutation)

    ops._ledger.record_transaction.assert_awaited_once()
    kwargs = ops._ledger.record_transaction.await_args.kwargs
    assert kwargs["project"] == "cortex-evolution"
    assert kwargs["action"] == "evolution_checkpoint"
    assert kwargs["detail"]["agent_id"] == "agent-omega"
    assert kwargs["detail"]["mutation_id"] == "mut-001"
    assert agent.mutations == []


def test_ledger_record_cli_awaits_async_write(monkeypatch) -> None:
    runner = CliRunner()
    ledger = SimpleNamespace(record_transaction=AsyncMock(return_value="hash-123"))
    engine = SimpleNamespace(
        ledger=ledger,
        init_db=AsyncMock(),
        close=AsyncMock(),
    )

    monkeypatch.setattr("cortex.cli.ledger.get_engine", lambda db: engine)
    monkeypatch.setattr("cortex.cli.ledger._run_async", lambda coro: asyncio.run(coro))

    result = runner.invoke(
        ledger_cmds,
        [
            "record",
            "--project",
            "proj-x",
            "--action",
            "manual_event",
            "--detail",
            '{"ok": true}',
        ],
    )

    assert result.exit_code == 0
    ledger.record_transaction.assert_awaited_once_with("proj-x", "manual_event", {"ok": True})
    assert "Transaction recorded." in result.output
