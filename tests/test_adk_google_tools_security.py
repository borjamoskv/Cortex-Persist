from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "module_name",
    ["cortex.adk.goog_tools", "cortex.extensions.adk.goog_tools"],
)
def test_notebooklm_sync_forwards_tenant_to_cli(module_name: str, monkeypatch) -> None:
    module = importlib.import_module(module_name)
    captured: dict[str, object] = {}

    def fake_run(cmd, capture_output: bool, text: bool, check: bool):
        captured["cmd"] = cmd
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["check"] = check

        class _Result:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return _Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module.goog_sync_notebooklm(mode="domains", tenant_id="tenant-alpha")

    assert result["status"] == "success"
    assert captured["cmd"] == [
        "cortex",
        "notebooklm",
        "sync",
        "--mode",
        "domains",
        "--tenant-id",
        "tenant-alpha",
    ]


@pytest.mark.parametrize(
    "module_name",
    ["cortex.adk.goog_tools", "cortex.extensions.adk.goog_tools"],
)
def test_notebooklm_sync_rejects_invalid_mode(module_name: str) -> None:
    module = importlib.import_module(module_name)

    result = module.goog_sync_notebooklm(mode="everything")

    assert result == {"status": "error", "message": "Invalid mode. Use digest, domains, or both."}


@pytest.mark.parametrize(
    "module_name",
    ["cortex.adk.goog_tools", "cortex.extensions.adk.goog_tools"],
)
def test_google_backup_is_blocked_without_explicit_opt_in(module_name: str, monkeypatch) -> None:
    module = importlib.import_module(module_name)
    monkeypatch.delenv("CORTEX_ALLOW_FULL_DB_CLOUD_BACKUP", raising=False)

    result = module.goog_backup_cortex()

    assert result["status"] == "error"
    assert "disabled by default" in result["message"]


@pytest.mark.parametrize(
    "module_name",
    ["cortex.adk.goog_tools", "cortex.extensions.adk.goog_tools"],
)
def test_google_backup_requires_out_of_band_env_opt_in_before_copying_full_db(
    module_name: str, tmp_path: Path, monkeypatch
) -> None:
    module = importlib.import_module(module_name)
    home = tmp_path / "home"
    cortex_dir = home / ".cortex"
    cortex_dir.mkdir(parents=True)
    (cortex_dir / "cortex.db").write_bytes(b"db bytes")
    (cortex_dir / "context-snapshot.md").write_text("snapshot", encoding="utf-8")
    drive = tmp_path / "drive" / "CORTEX-NotebookLM"
    drive.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CORTEX_ALLOW_FULL_DB_CLOUD_BACKUP", "1")
    monkeypatch.setattr(module, "_detect_cloud_sync", lambda: (drive, "Google Drive"))

    result = module.goog_backup_cortex()

    assert result["status"] == "success"
    backup_dir = drive / "backups"
    assert list(backup_dir.glob("cortex_sovereign_backup_*.db"))
    assert list(backup_dir.glob("context-snapshot_*.md"))
