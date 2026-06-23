# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from babylon60 import __version__ as CORTEX_VERSION
from babylon60.database.core import connect_async, load_sqlite_vec_async


def _blocked_import_env(tmp_path: Path, blocked_modules: list[str]) -> dict[str, str]:
    repo_root = Path(__file__).resolve().parents[1]
    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        "\n".join(
            [
                "import builtins",
                "import os",
                "import sys",
                "",
                "# Chain the standard sitecustomize if present",
                "curr_dir = os.path.dirname(__file__)",
                "for path in sys.path:",
                "    if path and path != curr_dir:",
                "        candidate = os.path.join(path, 'sitecustomize.py')",
                "        if os.path.isfile(candidate):",
                "            try:",
                "                with open(candidate, 'rb') as f:",
                "                    code = compile(f.read(), candidate, 'exec')",
                "                    exec(code, globals())",
                "            except Exception:",
                "                pass",
                "            break",
                "",
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
                "from babylon60.memory.models import MemoryEvent; "
                "from babylon60.memory.working import WorkingMemoryL1; "
                "from babylon60.memory.ledger import EventLedgerL3; "
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
                    "from babylon60.engine import CortexEngine",
                    "from babylon60.observability.jsonl_logger import setup_cortex_logging",
                    f"db_path = r'{db_path}'",
                    "setup_cortex_logging()",
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
                    "from babylon60.cli.main import cli",
                    "from babylon60.observability.jsonl_logger import setup_cortex_logging",
                    "setup_cortex_logging()",
                    f"db_path = r'{db_path}'",
                    "result = CliRunner().invoke(cli, ['init', '--db', db_path])",
                    "print(result.output)",
                    "if result.exception:",
                    "    import traceback",
                    "    print('EXCEPTION:', repr(result.exception))",
                    "    traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)",
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


@pytest.mark.timeout(120)
def test_cli_base_flow_without_extended_runtime_dependencies(tmp_path: Path) -> None:
    env = _blocked_import_env(
        tmp_path,
        [
            "aiofiles",
            "aiohttp",
            "bs4",
            "arq",
            "email_validator",
            "watchdog",
            "yaml",
            "pythonosc",
            "radon",
            "neo4j",
            "prometheus_client",
        ],
    )
    env["CORTEX_NO_EMBED"] = "1"
    env["CORTEX_LLM_PROVIDER"] = ""
    env["CORTEX_MASTER_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    env["CORTEX_TESTING"] = "1"
    for k in [
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "DEEPSEEK_API_KEY",
    ]:
        env.pop(k, None)
    db_path = tmp_path / "base-flow.db"
    commands = [
        ["--version"],
        ["init", "--db", str(db_path)],
        ["memory", "store", "demo-project", "base flow fact", "--db", str(db_path)],
        ["trust-ledger", "verify", "--db", str(db_path)],
    ]

    combined = ""
    for cmd in commands:
        result = subprocess.run(
            [sys.executable, "-m", "cortex"] + cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        combined += result.stdout + result.stderr
        assert result.returncode == 0, (
            f"Command {cmd} failed. Output:\n{result.stdout}\n{result.stderr}"
        )
    assert "blocked by test harness" not in combined
    assert "ImportError" not in combined
    assert f"CORTEX v{CORTEX_VERSION} initialized" in combined
    assert "Stored fact" in combined
    assert "Ledger is VALID" in combined


@pytest.mark.timeout(120)
def test_cli_base_flow_without_keyring_when_env_master_key_is_set(tmp_path: Path) -> None:
    env = _blocked_import_env(tmp_path, ["keyring", "AppKit", "Foundation", "Cocoa", "objc"])
    env["CORTEX_NO_EMBED"] = "1"
    env["CORTEX_LLM_PROVIDER"] = ""
    env["CORTEX_MASTER_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    env["CORTEX_TESTING"] = "1"
    for k in [
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "DEEPSEEK_API_KEY",
    ]:
        env.pop(k, None)
    db_path = tmp_path / "env-master-key.db"
    commands = [
        ["--version"],
        ["init", "--db", str(db_path)],
        ["memory", "store", "demo-project", "env key fact", "--db", str(db_path)],
        ["trust-ledger", "verify", "--db", str(db_path)],
    ]

    combined = ""
    for cmd in commands:
        result = subprocess.run(
            [sys.executable, "-m", "cortex"] + cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        combined += result.stdout + result.stderr
        assert result.returncode == 0, (
            f"Command {cmd} failed. Output:\n{result.stdout}\n{result.stderr}"
        )
    assert "ImportError: keyring blocked by test harness" not in combined
    assert f"CORTEX v{CORTEX_VERSION} initialized" in combined
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
                    "import babylon60.mcp",
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
