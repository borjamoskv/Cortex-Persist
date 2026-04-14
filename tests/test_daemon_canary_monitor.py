import stat
from pathlib import Path

import cortex.extensions.daemon.monitors.canary as canary_module


def test_canary_monitor_creates_restricted_canary_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    canary_path = tmp_path / "canaries" / "secrets.env"
    monkeypatch.setattr(canary_module, "CANARY_FILES", [canary_path])

    canary_module.CanaryMonitor()

    assert canary_path.exists()
    content = canary_path.read_text(encoding="utf-8")
    assert "STRIKE_KEY=" in content
    assert stat.S_IMODE(canary_path.stat().st_mode) == 0o600
