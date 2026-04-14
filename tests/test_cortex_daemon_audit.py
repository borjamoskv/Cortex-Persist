import asyncio
import importlib.util
import inspect
import json
from pathlib import Path


def _load_cortex_daemon_module():
    module_path = (
        Path(__file__).resolve().parents[1] / "cortex-core" / "cortex_daemon.py"
    )
    spec = importlib.util.spec_from_file_location("cortex_daemon_module", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_self_audit_uses_exec_not_shell() -> None:
    module = _load_cortex_daemon_module()

    source = inspect.getsource(module.CortexDaemon._run_self_audit)

    assert "create_subprocess_exec" in source
    assert "create_subprocess_shell" not in source
    assert 'with open(error_log, "w")' not in source


def test_self_audit_queues_optimizer_when_report_is_unstable(monkeypatch) -> None:
    module = _load_cortex_daemon_module()
    daemon = module.CortexDaemon()
    queued: list[tuple[str, str]] = []

    class DummyProcess:
        returncode = 0

        async def communicate(self):
            report = {"status": "UNSTABLE", "exergy_score": 12}
            return json.dumps(report).encode(), b""

    async def fake_create_subprocess_exec(*args, **kwargs):
        assert args[0] == "python3"
        assert args[1].endswith("mirror_audit.py")
        assert args[2].endswith("cortex_daemon.py")
        return DummyProcess()

    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setattr(
        daemon,
        "_queue_task",
        lambda agent, cmd: queued.append((agent, cmd)),
    )

    asyncio.run(daemon._run_self_audit())

    assert queued
    assert queued[0][0] == "OPTIMIZER"
    assert "remediator.py" in queued[0][1]


def test_execute_task_uses_exec_not_shell() -> None:
    module = _load_cortex_daemon_module()

    source = inspect.getsource(module.CortexDaemon._execute_task)

    assert "create_subprocess_exec" in source
    assert "create_subprocess_shell" not in source
    assert 'with open(jit_jail_path, "w")' not in source


def test_cortex_daemon_uses_sovereign_run_in_entrypoint() -> None:
    module = _load_cortex_daemon_module()
    source = inspect.getsource(module)

    assert "sovereign_run(daemon.run())" in source
    assert "set_event_loop_policy" not in source
    assert "EventLoopPolicy" not in source
