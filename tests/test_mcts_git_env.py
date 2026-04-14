import asyncio
import inspect
from pathlib import Path

from cortex.mcts.git_env import MCTSGitEnvironment
import cortex.mcts.git_env as git_env_module


class _DummyProcess:
    def __init__(self, returncode: int, stdout: bytes = b"", stderr: bytes = b"") -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


def test_branch_out_uses_exec_and_falls_back_to_existing_branch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[object, ...]] = []
    processes = [
        _DummyProcess(returncode=1),
        _DummyProcess(returncode=0),
    ]

    async def fake_create_subprocess_exec(*args, **kwargs):
        calls.append(args)
        return processes.pop(0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    target = tmp_path / "module.py"
    target.write_text("print('ok')\n", encoding="utf-8")
    env = MCTSGitEnvironment(router=None, target_file=target)

    branch = asyncio.run(env.branch_out("main", "abc123"))

    assert branch == "chronos/node-abc123"
    assert calls == [
        ("git", "checkout", "-b", "chronos/node-abc123", "main"),
        ("git", "checkout", "chronos/node-abc123"),
    ]


def test_simulate_uses_exec_for_ruff_and_pytest(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[object, ...]] = []
    processes = [
        _DummyProcess(returncode=0),
        _DummyProcess(returncode=0),
    ]

    async def fake_create_subprocess_exec(*args, **kwargs):
        calls.append(args)
        return processes.pop(0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    target = tmp_path / "module.py"
    target.write_text("print('ok')\n", encoding="utf-8")
    env = MCTSGitEnvironment(router=None, target_file=target)

    reward = asyncio.run(env.simulate())

    assert reward == 1.0
    assert calls == [
        ("ruff", "check", str(target.resolve())),
        ("pytest", "tests/", "-v", "-q", "--tb=no"),
    ]


def test_mutate_updates_target_file_atomically(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text("print('old')\n", encoding="utf-8")

    class _DummyResult:
        def __init__(self, content: str) -> None:
            self._content = content

        def is_err(self) -> bool:
            return False

        def unwrap(self) -> str:
            return self._content

    class _DummyRouter:
        async def execute_resilient(self, prompt):
            return _DummyResult("```python\nprint('new')\n```\n")

    env = MCTSGitEnvironment(router=_DummyRouter(), target_file=target)

    changed = asyncio.run(env.mutate("rewrite print"))

    assert changed is True
    assert target.read_text(encoding="utf-8") == "print('new')"
    source = inspect.getsource(git_env_module.MCTSGitEnvironment.mutate)
    assert ".write_text(" not in source
