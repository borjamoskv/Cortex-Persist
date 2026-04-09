from __future__ import annotations

import importlib

import pytest

import cortex.core.paths as paths


@pytest.fixture(autouse=True)
def _restore_paths_module():
    yield
    importlib.reload(paths)


def test_cortex_db_prefers_cortex_db_path(monkeypatch, tmp_path) -> None:
    preferred = tmp_path / "preferred.db"
    fallback = tmp_path / "fallback.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(preferred))
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    reloaded = importlib.reload(paths)

    assert reloaded.CORTEX_DB == preferred


def test_cortex_db_falls_back_to_legacy_env(monkeypatch, tmp_path) -> None:
    fallback = tmp_path / "fallback.db"
    monkeypatch.delenv("CORTEX_DB_PATH", raising=False)
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    reloaded = importlib.reload(paths)

    assert reloaded.CORTEX_DB == fallback


def test_resolve_native_binary_prefers_env_override(monkeypatch, tmp_path) -> None:
    binary = tmp_path / "cortex-db"
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("CORTEX_NATIVE_DB_BIN", str(binary))

    assert paths.resolve_native_binary("cortex-db", "CORTEX_NATIVE_DB_BIN") == binary


def test_resolve_native_binary_uses_build_cache(monkeypatch) -> None:
    binary_name = "cortex-test-bin"
    build_bin = paths.Path(paths.__file__).resolve().parents[2] / "build" / "native" / "bin" / binary_name
    build_bin.parent.mkdir(parents=True, exist_ok=True)
    build_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    build_bin.chmod(0o755)
    monkeypatch.delenv("CORTEX_NATIVE_DB_BIN", raising=False)
    monkeypatch.delenv("CORTEX_DB_BIN", raising=False)
    monkeypatch.setattr(paths.shutil, "which", lambda _: None)

    try:
        assert paths.resolve_native_binary(binary_name, "CORTEX_NATIVE_DB_BIN", "CORTEX_DB_BIN") == build_bin
    finally:
        build_bin.unlink(missing_ok=True)


def test_resolve_skill_dir_uses_alias_when_exact_dir_is_missing(monkeypatch, tmp_path) -> None:
    (tmp_path / "CORTEX-Orchestra-Omega").mkdir()
    monkeypatch.setenv("CORTEX_SKILLS_DIR", str(tmp_path))

    reloaded = importlib.reload(paths)

    assert reloaded.resolve_skill_dir("keter-omega") == tmp_path / "CORTEX-Orchestra-Omega"
    assert reloaded.resolve_skill_name("keter-omega") == "CORTEX-Orchestra-Omega"


def test_resolve_skill_dir_prefers_exact_dir_over_alias(monkeypatch, tmp_path) -> None:
    (tmp_path / "keter-omega").mkdir()
    (tmp_path / "CORTEX-Orchestra-Omega").mkdir()
    monkeypatch.setenv("CORTEX_SKILLS_DIR", str(tmp_path))

    reloaded = importlib.reload(paths)

    assert reloaded.resolve_skill_dir("keter-omega") == tmp_path / "keter-omega"
    assert reloaded.resolve_skill_name("keter-omega") == "keter-omega"


def test_find_skill_path_searches_alias_directories(monkeypatch, tmp_path) -> None:
    skill_dir = tmp_path / "Cognitive-Crystallizer-Omega" / "scripts"
    skill_dir.mkdir(parents=True)
    script_path = skill_dir / "singularity_engine.py"
    script_path.write_text("# test\n", encoding="utf-8")
    monkeypatch.setenv("CORTEX_SKILLS_DIR", str(tmp_path))

    reloaded = importlib.reload(paths)

    assert reloaded.find_skill_path("singularity-nexus", "scripts/singularity_engine.py") == script_path


def test_canonical_skill_name_maps_installed_aliases() -> None:
    assert paths.canonical_skill_name("CORTEX-Orchestra-Omega") == "keter-omega"
    assert paths.canonical_skill_name("Comms-Hub-Omega") == "comms-hub-omega"
