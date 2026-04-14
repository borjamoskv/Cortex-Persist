import importlib.util
import json
from pathlib import Path

import pytest

from cortex.extensions.daemon.models import DaemonStatus
from cortex.extensions.daemon.monitors.auto_immune import AutoImmuneMonitor
from cortex.extensions.daemon.state import DaemonState
import cortex.extensions.daemon.state as daemon_state_module
import cortex.mcp.singularity_tools as singularity_tools


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cortex_daemon_log_execution_persists_last_100_entries(tmp_path: Path) -> None:
    module = _load_module(
        "cortex_daemon_module",
        Path(__file__).resolve().parents[1] / "cortex-core" / "cortex_daemon.py",
    )
    daemon = module.CortexDaemon()
    ledger_path = tmp_path / "execution_ledger.json"
    module.EXECUTION_LEDGER = str(ledger_path)

    for idx in range(105):
        daemon._log_execution({"id": idx})

    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert len(data) == 100
    assert data[0]["id"] == 5
    assert data[-1]["id"] == 104


def test_vanguard_update_ledger_rewrites_atomically(tmp_path: Path) -> None:
    module = _load_module(
        "cortex_vanguard_daemon_module",
        Path(__file__).resolve().parents[1]
        / "engine-c5"
        / "cortex_vanguard_daemon.py",
    )
    ledger_path = tmp_path / "vanguard_ledger.json"
    module.LEDGER_PATH = str(ledger_path)

    module.update_ledger("target-a", "ok", "details")

    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert data["target-a"]["status"] == "ok"
    assert data["target-a"]["details"] == "details"


def test_singularity_ledger_append_persists_state_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registered_tools = {}

    class FakeMCP:
        def tool(self):
            def decorator(fn):
                registered_tools[fn.__name__] = fn
                return fn

            return decorator

    singularity_tools.STATE_FILE = str(tmp_path / "cortex_state.json")
    singularity_tools._LEDGER_STATE = None

    class DummyConn:
        def close(self) -> None:
            return None

    monkeypatch.setattr(singularity_tools.sqlite3, "connect", lambda *args, **kwargs: DummyConn())

    class DummyBus:
        def __init__(self, conn) -> None:
            self.conn = conn

        def emit(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(singularity_tools, "SignalBus", DummyBus)
    singularity_tools.register_singularity_tools(FakeMCP())

    result = registered_tools["cortex_ledger_append"]("mine", "bounty", 3.5)

    assert "Ledger entry created" in result
    state = json.loads(Path(singularity_tools.STATE_FILE).read_text(encoding="utf-8"))
    assert len(state["ledgers"]) == 1
    assert state["ledgers"][0]["vector_id"] == "bounty"


def test_daemon_state_save_state_writes_handoff_json(tmp_path: Path) -> None:
    daemon_state_module.CORTEX_ROOT = tmp_path
    state = DaemonState()
    state.daemons["cortex"]["handshake"] = "active"

    state.save_state()

    handoff = json.loads((tmp_path / "handoff.json").read_text(encoding="utf-8"))
    assert handoff["cortex"]["handshake"] == "active"


def test_moskv_daemon_save_status_writes_status_json(tmp_path: Path) -> None:
    module = _load_module(
        "moskv_daemon_core_module",
        Path(__file__).resolve().parents[1] / "cortex" / "extensions" / "daemon" / "core.py",
    )
    module.STATUS_FILE = tmp_path / "status.json"
    status = DaemonStatus(checked_at="2026-04-14T00:00:00+00:00")

    module.MoskvDaemon._save_status(object(), status)

    data = json.loads(module.STATUS_FILE.read_text(encoding="utf-8"))
    assert data["checked_at"] == "2026-04-14T00:00:00+00:00"


def test_auto_immune_monitor_save_ghosts_writes_file(tmp_path: Path) -> None:
    ghosts_path = tmp_path / "memory" / "ghosts.json"
    monitor = AutoImmuneMonitor(queue=None, ghosts_path=ghosts_path)

    monitor._save_ghosts({"demo": {"blocked_by": "AETHER[1]"}})

    data = json.loads(ghosts_path.read_text(encoding="utf-8"))
    assert data["demo"]["blocked_by"] == "AETHER[1]"
