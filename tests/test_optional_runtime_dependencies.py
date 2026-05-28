from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from cortex.database.core import connect_async, load_sqlite_vec_async


def _blocked_import_env(tmp_path: Path, blocked_modules: list[str]) -> dict[str, str]:
    repo_root = Path(__file__).resolve().parents[1]
    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        "\n".join(
            [
                "import builtins",
                "_real_import = builtins.__import__",
                f"_blocked_prefixes = {tuple(blocked_modules)!r}",
                "def _blocked(name, globals=None, locals=None, fromlist=(), level=0):",
                "    for prefix in _blocked_prefixes:",
                "        if name == prefix or name.startswith(prefix + '.'):",
                "            raise ImportError(f'{prefix} blocked by test harness')",
                "    return _real_import(name, globals, locals, fromlist, level)",
                "builtins.__import__ = _blocked",
            ]
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{tmp_path}:{repo_root}" if not pythonpath else f"{tmp_path}:{repo_root}:{pythonpath}"
    )
    return env


def _blocked_numpy_env(tmp_path: Path) -> dict[str, str]:
    return _blocked_import_env(tmp_path, ["numpy"])


def test_memory_imports_without_numpy(tmp_path: Path) -> None:
    env = _blocked_numpy_env(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from cortex.memory.models import MemoryEvent; "
                "from cortex.memory.working import WorkingMemoryL1; "
                "from cortex.memory.ledger import EventLedgerL3; "
                "WorkingMemoryL1(); "
                "MemoryEvent(role='user', content='x', token_count=1, session_id='s'); "
                "print('ok')"
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_engine_init_without_numpy_stays_quiet_about_optional_l2(tmp_path: Path) -> None:
    env = _blocked_numpy_env(tmp_path)
    db_path = tmp_path / "quiet-init.db"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "import asyncio",
                    "import logging",
                    "from cortex.engine import CortexEngine",
                    f"db_path = r'{db_path}'",
                    "logging.basicConfig(level=logging.INFO)",
                    "",
                    "async def main():",
                    "    engine = CortexEngine(db_path=db_path)",
                    "    try:",
                    "        await engine.init_db()",
                    "    finally:",
                    "        await engine.close()",
                    "",
                    "asyncio.run(main())",
                ]
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "Memory L2 unavailable" not in combined
    assert "Skipping schema statement: no such module: vec0" not in combined
    assert combined.count("Memory subsystem: partial (L1+L3)") == 1


def test_cli_init_without_numpy_logs_partial_memory_once(tmp_path: Path) -> None:
    env = _blocked_numpy_env(tmp_path)
    db_path = tmp_path / "cli-init.db"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "import logging",
                    "from click.testing import CliRunner",
                    "from cortex.cli.main import cli",
                    "logging.basicConfig(level=logging.INFO)",
                    f"db_path = r'{db_path}'",
                    "result = CliRunner().invoke(cli, ['init', '--db', db_path])",
                    "print(result.output)",
                    "raise SystemExit(result.exit_code)",
                ]
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "Memory L2 unavailable" not in combined
    assert "Skipping schema statement: no such module: vec0" not in combined
    assert combined.count("Memory subsystem: partial (L1+L3)") == 1


def test_cli_base_flow_without_extended_runtime_dependencies(tmp_path: Path) -> None:
    env = _blocked_import_env(
        tmp_path,
        ["aiofiles", "aiohttp", "bs4", "arq", "email_validator", "watchdog", "yaml"],
    )
    env["CORTEX_NO_EMBED"] = "1"
    db_path = tmp_path / "base-flow.db"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "from click.testing import CliRunner",
                    "from cortex.cli.main import cli",
                    f"db_path = r'{db_path}'",
                    "runner = CliRunner()",
                    "commands = [",
                    "    ['--version'],",
                    "    ['init', '--db', db_path],",
                    "    ['memory', 'store', 'demo-project', 'base flow fact', '--db', db_path],",
                    "    ['trust-ledger', 'verify', '--db', db_path],",
                    "]",
                    "for cmd in commands:",
                    "    result = runner.invoke(cli, cmd)",
                    "    print(result.output)",
                    "    if result.exception:",
                    "        raise result.exception",
                    "    if result.exit_code:",
                    "        raise SystemExit(result.exit_code)",
                ]
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "blocked by test harness" not in combined
    assert "ImportError" not in combined
    assert "CORTEX v0.3.0b7 initialized" in combined
    assert "Stored fact" in combined
    assert "Ledger is VALID" in combined


def test_cli_base_flow_without_keyring_when_env_master_key_is_set(tmp_path: Path) -> None:
    env = _blocked_import_env(tmp_path, ["keyring", "AppKit", "Foundation", "Cocoa", "objc"])
    env["CORTEX_NO_EMBED"] = "1"
    env["CORTEX_MASTER_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    db_path = tmp_path / "env-master-key.db"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "from click.testing import CliRunner",
                    "from cortex.cli.main import cli",
                    f"db_path = r'{db_path}'",
                    "runner = CliRunner()",
                    "commands = [",
                    "    ['--version'],",
                    "    ['init', '--db', db_path],",
                    "    ['memory', 'store', 'demo-project', 'env key fact', '--db', db_path],",
                    "    ['trust-ledger', 'verify', '--db', db_path],",
                    "]",
                    "for cmd in commands:",
                    "    result = runner.invoke(cli, cmd)",
                    "    print(result.output)",
                    "    if result.exception:",
                    "        raise result.exception",
                    "    if result.exit_code:",
                    "        raise SystemExit(result.exit_code)",
                ]
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "ImportError: keyring blocked by test harness" not in combined
    assert "CORTEX v0.3.0b7 initialized" in combined
    assert "Stored fact" in combined
    assert "Ledger is VALID" in combined


def test_mcp_package_import_is_lazy(tmp_path: Path) -> None:
    env = _blocked_import_env(tmp_path, ["mcp.server.fastmcp", "markdownify", "bs4", "aiohttp"])

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "import sys",
                    "import cortex.mcp",
                    "assert 'aiohttp' not in sys.modules",
                    "assert 'bs4' not in sys.modules",
                    "assert 'markdownify' not in sys.modules",
                    "print('ok')",
                ]
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


@pytest.mark.asyncio
async def test_async_sqlite_vec_loader_enables_vec0(tmp_path: Path) -> None:
    conn = await connect_async(str(tmp_path / "vec_bootstrap.db"))
    try:
        if not await load_sqlite_vec_async(conn):
            pytest.skip("sqlite-vec unavailable in this runtime")

        await conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS test_vec USING vec0(embedding float[4])"
        )
        await conn.commit()
    finally:
        await conn.close()
