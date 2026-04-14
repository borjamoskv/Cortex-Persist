import asyncio
import importlib.util
from pathlib import Path


def _load_vanguard_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "engine-c5"
        / "cortex_vanguard_daemon.py"
    )
    spec = importlib.util.spec_from_file_location("cortex_vanguard_daemon_module", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DummyProcess:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode

    async def communicate(self):
        return b"ok", b""


def test_run_step_uses_exec_wrapper_for_sandboxed_commands(monkeypatch) -> None:
    module = _load_vanguard_module()
    calls: list[tuple[object, ...]] = []

    async def fake_create_subprocess_exec(*args, **kwargs):
        calls.append(args)
        return _DummyProcess()

    monkeypatch.setattr(module, "_classify_cmd", lambda cmd, phase: True)
    monkeypatch.setattr(module, "_sandbox_cmd", lambda cmd, cwd: ("echo hi", "/tmp/arena"))
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    output = asyncio.run(module.run_step("scan", ["echo", "hi"]))

    assert output == "ok"
    assert calls == [("/bin/sh", "-lc", "echo hi")]
