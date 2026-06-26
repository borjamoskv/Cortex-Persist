from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import native_paths


def test_resolve_native_binary_prefers_env_override(monkeypatch, tmp_path) -> None:
    binary = tmp_path / "cortex-db"
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("CORTEX_NATIVE_DB_BIN", str(binary))

    assert native_paths.resolve_native_binary("cortex-db", "CORTEX_NATIVE_DB_BIN") == binary


def test_resolve_native_binary_uses_build_cache(monkeypatch) -> None:
    binary_name = "cortex-test-bin"
    build_bin = native_paths.BUILD_NATIVE_BIN / binary_name
    build_bin.parent.mkdir(parents=True, exist_ok=True)
    build_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    build_bin.chmod(0o755)
    monkeypatch.delenv("CORTEX_NATIVE_DB_BIN", raising=False)
    monkeypatch.delenv("CORTEX_DB_BIN", raising=False)
    monkeypatch.setattr(native_paths.shutil, "which", lambda _: None)

    try:
        assert (
            native_paths.resolve_native_binary(
                binary_name,
                "CORTEX_NATIVE_DB_BIN",
                "CORTEX_DB_BIN",
            )
            == build_bin
        )
    finally:
        build_bin.unlink(missing_ok=True)


def test_resolve_project_script_defaults_to_repo_scripts() -> None:
    path = native_paths.resolve_project_script("agent_hound_omega.py")
    assert path == ROOT / "scripts" / "agent_hound_omega.py"
