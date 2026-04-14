import asyncio
import sys
from pathlib import Path

import foundry_c5_engine
from foundry_c5_engine import OuroborosEngine


def test_engine_keeps_legacy_constructor_contract() -> None:
    engine = OuroborosEngine(target_url="https://example.com/repo.git", worker_id="w1")

    assert engine.target_url == "https://example.com/repo.git"
    assert engine.worker_id == "w1"
    assert hasattr(engine, "run_audit")


def test_setup_forge_environment_passes_repo_as_single_exec_arg(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    async def fake_run_exec(self, *cmd: str, cwd: Path) -> tuple[int, str, str]:
        calls.append(cmd)
        return 0, "", ""

    monkeypatch.setattr(OuroborosEngine, "_run_exec", fake_run_exec)

    async def run() -> None:
        engine = OuroborosEngine()
        await engine.setup_forge_environment(
            "https://example.com/repo.git; touch /tmp/should_not_execute; #"
        )

    asyncio.run(run())

    assert calls[0][:3] == ("forge", "init", "--force")
    assert calls[1][0] == "git"
    assert calls[1][1] == "clone"
    assert calls[1][4] == "https://example.com/repo.git; touch /tmp/should_not_execute; #"


def test_main_accepts_target_alias(monkeypatch) -> None:
    async def fake_run_audit(self, repo_url=None, log_callback=None):
        return {"status": "COMPLETED"}

    monkeypatch.setattr(OuroborosEngine, "run_audit", fake_run_audit)
    monkeypatch.setattr(
        sys,
        "argv",
        ["foundry_c5_engine.py", "--target", "https://example.com/repo.git"],
    )

    assert asyncio.run(foundry_c5_engine.main()) == 0
