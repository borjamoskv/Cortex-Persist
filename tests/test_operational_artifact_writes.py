import asyncio
import importlib.util
import inspect
import subprocess
from pathlib import Path


def _load_module(module_name: str, relative_path: str):
    module_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ouroboros_engine_generates_fuzz_test_and_uses_exec_for_init(tmp_path: Path) -> None:
    module = _load_module("ouroboros_engine_module", "cortex-core/ouroboros_engine.py")
    engine = module.OuroborosEngine()
    engine.scratch_dir = str(tmp_path)
    contract_file = tmp_path / "src" / "Vault.sol"
    contract_file.parent.mkdir(parents=True)
    contract_file.write_text("contract Vault {}", encoding="utf-8")

    test_file = asyncio.run(engine.generate_fuzz_test("Vault", str(contract_file)))

    content = Path(test_file).read_text(encoding="utf-8")
    assert "contract VaultOuroborosTest is Test" in content
    assert "create_subprocess_exec" in inspect.getsource(module.OuroborosEngine.run_audit)
    assert "os.system" not in inspect.getsource(module.OuroborosEngine.run_audit)


def test_install_linux_writes_unit_file(monkeypatch, tmp_path: Path) -> None:
    module = _load_module("daemon_platform_module", "cortex/extensions/daemon/platform.py")
    unit_path = tmp_path / "moskv.service"
    calls = []

    monkeypatch.setattr(module, "_get_systemd_unit", lambda: unit_path)
    monkeypatch.setattr(module.sys, "executable", "/usr/bin/python3")
    monkeypatch.setattr(module.console, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr(subprocess, "run", lambda cmd, check=False: calls.append(tuple(cmd)))
    module.install_linux()

    content = unit_path.read_text(encoding="utf-8")
    assert "ExecStart=/usr/bin/python3 -m cortex.daemon_cli start" in content
    assert ("systemctl", "--user", "daemon-reload") in calls


def test_heartbeat_daemon_deposits_result_atomically(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        "heartbeat_daemon_module",
        "cortex/extensions/daemon/centaur/heartbeat.py",
    )
    monkeypatch.setattr(module, "ITURRIA_DIR", tmp_path)

    daemon = module.HeartbeatDaemon(queue=None, engine=None)  # type: ignore[arg-type]
    task = {"id": "abcdef123456", "type": "RESEARCH"}
    result = {"formation": "PHALANX", "agents_used": 3, "solution": "done"}

    daemon._deposit_to_iturria(task, result)

    files = list(tmp_path.glob("RESEARCH_*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "Task ID:** abcdef123456" in content
    assert "Formation:** PHALANX" in content
