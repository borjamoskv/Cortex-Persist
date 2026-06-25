# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from legacy_research.guards.sovereign_seals import (
    _resolve_git_hook_path,
    _parse_pyproject_deps,
    _extract_imports,
    check_seal_8_dependency_impl,
    check_seal_9_compliance_impl,
    check_gate_21_preservation,
)


def test_resolve_git_hook_path(tmp_path):
    with (
        patch("cortex.guards.sovereign_seals.ROOT_DIR", tmp_path),
        patch("shutil.which", return_value=None),
    ):
        path = _resolve_git_hook_path("pre-push")
        assert "hooks/pre-push" in str(path)


def test_parse_pyproject_deps(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
dependencies = ["requests>=2.0", "rich"]
[project.optional-dependencies]
dev = ["pytest"]
""")
    with patch("cortex.guards.sovereign_seals.ROOT_DIR", tmp_path):
        deps = _parse_pyproject_deps()
        assert "requests" in deps
        assert "rich" in deps
        assert "pytest" in deps


def test_extract_imports():
    source = """
import os
from pathlib import Path
import json, sys
from legacy_research.guards import seals
"""
    imports = _extract_imports(source)
    assert "os" in imports
    assert "pathlib" in imports
    assert "json" in imports
    assert "sys" in imports
    assert "cortex" in imports or "cortex" in imports


@pytest.mark.asyncio
async def test_check_seal_8_dependency_impl_happy():
    cached_files = {Path("f.py"): "import os"}
    with patch("cortex.guards.sovereign_seals._parse_pyproject_deps", return_value={"requests"}):
        passed, status = await check_seal_8_dependency_impl(cached_files)
        assert passed is True
        assert status == "verified"


@pytest.mark.asyncio
async def test_check_seal_9_compliance_impl_happy():
    with (
        patch("cortex.engine.CortexEngine") as mock_engine,
        patch("cortex.guards.url_guard.is_safe_url", return_value=True),
    ):
        mock_engine.return_value.init_db = AsyncMock()
        mock_engine.return_value.close = AsyncMock()
        passed, status = await check_seal_9_compliance_impl()
        assert passed is True
        assert status == "verified"


@pytest.mark.asyncio
async def test_check_gate_21_preservation_happy(tmp_path):
    with (
        patch("cortex.guards.sovereign_seals.ROOT_DIR", tmp_path),
        patch("cortex.guards.sovereign_seals._resolve_git_hook_path") as mock_hook,
        patch("os.access", return_value=True),
        patch("shutil.which", return_value="git"),
        patch("subprocess.run") as mock_run,
    ):
        mock_hook.return_value.exists.return_value = True
        (tmp_path / "legacy_research/guards").mkdir(parents=True)
        (tmp_path / "legacy_research/guards/seals.py").write_text("code")

        mock_run.return_value.returncode = 0

        passed, status = await check_gate_21_preservation()
        assert passed is True
        assert status == "verified"
