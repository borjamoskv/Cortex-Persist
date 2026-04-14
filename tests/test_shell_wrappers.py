import asyncio
import inspect
from pathlib import Path

from cortex.extensions.daemon import actuators
from cortex.extensions.daemon.actuators import PhysicalActuator
from cortex.extensions.swarm.code_smith import LocalProcessSandbox
import cortex.mcp.aether_server as aether_server


class _AllowAllClassifier:
    def classify(self, command: str):
        class Verdict:
            blocked = False
            reason = ""

        return Verdict()


class _FakeProfile:
    def __str__(self) -> str:
        return "/tmp/cortex_prison.sb"

    def exists(self) -> bool:
        return True


def test_physical_actuator_wraps_shell_with_exec(monkeypatch) -> None:
    calls: list[tuple[object, ...]] = []

    class DummyProcess:
        returncode = 0

        async def communicate(self):
            return b"ok", b""

    async def fake_create_subprocess_exec(*args, **kwargs):
        calls.append(args)
        return DummyProcess()

    monkeypatch.setattr(actuators, "SHELL_CLASSIFIER", _AllowAllClassifier())
    monkeypatch.setattr(actuators, "_PRISON_PROFILE", _FakeProfile())
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    result = asyncio.run(PhysicalActuator.ekin_execute_shell("echo hi"))

    assert result["status"] == "success"
    assert calls == [
        (
            "sandbox-exec",
            "-f",
            "/tmp/cortex_prison.sb",
            "/bin/sh",
            "-lc",
            "echo hi",
        )
    ]


def test_local_process_sandbox_uses_exec_wrapper(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[tuple[object, ...], str | None]] = []

    class DummyProcess:
        returncode = 0

        async def communicate(self):
            return b"stdout", b""

    async def fake_create_subprocess_exec(*args, **kwargs):
        calls.append((args, kwargs.get("cwd")))
        return DummyProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    sandbox = LocalProcessSandbox(tmp_dir=tmp_path)
    result = asyncio.run(sandbox.run_command("pytest -q"))

    assert result.success is True
    assert calls == [(("/bin/sh", "-lc", "pytest -q"), str(tmp_path))]


def test_local_process_sandbox_write_file_persists_content(tmp_path: Path) -> None:
    sandbox = LocalProcessSandbox(tmp_dir=tmp_path)

    asyncio.run(sandbox.write_file("nested/test.py", "print('ok')\n"))

    assert (tmp_path / "nested" / "test.py").read_text(encoding="utf-8") == "print('ok')\n"
    source = inspect.getsource(LocalProcessSandbox.write_file)
    assert ".write_text(" not in source


def test_aether_server_uses_bash_exec_wrapper() -> None:
    source = inspect.getsource(aether_server.create_aether_server)

    assert '"/bin/bash"' in source
    assert "create_subprocess_exec" in source
    assert "create_subprocess_shell" not in source
