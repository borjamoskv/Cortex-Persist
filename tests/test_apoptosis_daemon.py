import asyncio
import os
import subprocess
from pathlib import Path

import pytest
from cortex.extensions.daemon.apoptosis_daemon import ApoptosisDaemon


@pytest.fixture
def dummy_repo(tmp_path):
    repo_dir = tmp_path / "repo"
    cortex_dir = repo_dir / "cortex"
    cortex_dir.mkdir(parents=True)

    # Create protected file that references consumer
    init_file = cortex_dir / "__init__.py"
    init_file.write_text("import cortex.consumer\n", encoding="utf-8")

    # Create an active module
    active_module = cortex_dir / "active_engine.py"
    active_module.write_text("class ActiveEngine:\n    pass\n", encoding="utf-8")

    # Create a consumer that references ActiveEngine
    consumer = cortex_dir / "consumer.py"
    consumer.write_text("from cortex.active_engine import ActiveEngine\n", encoding="utf-8")

    # Create a completely dead module
    dead_module = cortex_dir / "dead_logic.py"
    dead_module.write_text("def useless_function():\n    return 42\n", encoding="utf-8")

    yield repo_dir


@pytest.fixture
def mock_git(monkeypatch):
    def fake_run(*args, **kwargs):
        cmd = args[0]
        if "log" in cmd:
            # Fake that the file is old (timestamp 0 => 1970)
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="0\n")
        elif "rm" in cmd:
            # Fake successful git rm
            # Physically delete the file to simulate git rm
            filepath = Path(cmd[-1])
            if filepath.exists():
                filepath.unlink()
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)


@pytest.mark.asyncio
async def test_apoptosis_daemon(dummy_repo, mock_git):
    daemon = ApoptosisDaemon(repo_path=dummy_repo, db_path=":memory:")

    # Run the purge
    purged = await daemon.execute_purge()

    cortex_dir = dummy_repo / "cortex"

    # The dead module should be deleted
    assert not (cortex_dir / "dead_logic.py").exists()

    # The active and protected modules should remain
    assert (cortex_dir / "active_engine.py").exists()
    assert (cortex_dir / "consumer.py").exists()
    assert (cortex_dir / "__init__.py").exists()

    # Only 1 file should have been purged
    assert purged == 1


def test_ast_extraction(dummy_repo):
    daemon = ApoptosisDaemon(repo_path=dummy_repo, db_path=":memory:")
    dead_module = dummy_repo / "cortex" / "dead_logic.py"

    exports = daemon._extract_exports(dead_module)
    assert "useless_function" in exports
