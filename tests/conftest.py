# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import os
import sys
from pathlib import Path

# Set environment variables for tests globally before any imports/fixtures run
os.environ["CORTEX_TESTING"] = "1"
os.environ["CORTEX_TEST_ENV"] = "1"
os.environ["CORTEX_NO_OMEGA"] = "1"
os.environ["CORTEX_MASTER_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import pytest
import sqlite3

_raw_sqlite3_connect = sqlite3.connect

def _test_safe_sqlite3_connect(*args, **kwargs):
    """Enforce WAL and busy_timeout in tests to prevent flaky lock errors."""
    conn = _raw_sqlite3_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.Error:
        pass
    return conn

sqlite3.connect = _test_safe_sqlite3_connect

# ── Repo-local import resolution ──────────────────────────────────────────────
# Several legacy tests import modules that live outside the installed package
# surface. Resolve them relative to the checkout so CI doesn't depend on a
# developer-specific home directory layout.
_REPO_ROOT = Path(__file__).resolve().parents[1]
for extra_path in (
    _REPO_ROOT,
    _REPO_ROOT / "cortex-core",
    _REPO_ROOT / "scripts" / "sortu",
):
    if extra_path.exists() and str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))


@pytest.fixture(autouse=True)
def mock_local_embedder(monkeypatch):
    """Mock the local embedder to prevent 10s ONNX model loads during every test."""

    class DummyEmbedder:
        def embed(self, content: str | list[str]) -> list[float] | list[list[float]]:
            if isinstance(content, str):
                return [0.0] * 384
            return [[0.0] * 384 for _ in content]

        async def aembed(self, content: str | list[str]) -> list[float] | list[list[float]]:
            if isinstance(content, str):
                return [0.0] * 384
            return [[0.0] * 384 for _ in content]

    from cortex.engine import CortexEngine

    monkeypatch.setattr(CortexEngine, "_get_embedder", lambda self: DummyEmbedder())


@pytest.fixture(autouse=True)
def reset_anomaly_detector():
    """Reset the anomaly detector before each test to prevent bulk mutation blocks."""
    from cortex_extensions.security.anomaly_detector import DETECTOR

    DETECTOR.reset()


@pytest.fixture(autouse=True)
def inject_test_master_key(monkeypatch):
    """Ensure a deterministic Master Key is available for tests."""
    monkeypatch.setenv("CORTEX_TESTING", "1")
    monkeypatch.setenv("CORTEX_NO_OMEGA", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "1")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test")
    # Base64 for 32 bytes of '0'
    monkeypatch.setenv("CORTEX_MASTER_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")

@pytest.fixture(autouse=True)
def isolate_swarm_ledger(tmp_path, monkeypatch):
    """Ensure each test gets an isolated SwarmLedger database."""
    db_path = tmp_path / "swarm_ledger.db"
    monkeypatch.setenv("CORTEX_SWARM_DB_PATH", str(db_path))


def pytest_configure(config):
    """Optimize pytest collection and execution on macOS."""
    import gc
    import sys
    import warnings

    sys.settrace(None)
    sys.setprofile(None)
    gc.freeze()
    warnings.filterwarnings("ignore", category=pytest.PytestUnhandledThreadExceptionWarning)


def pytest_sessionfinish(session, exitstatus):
    """Save exit status before finalization."""
    session.config.exitstatus = exitstatus


def pytest_unconfigure(config):
    """Force exit to prevent finalization hangs on leaked daemon threads."""
    if hasattr(config, "workerinput"):
        return
    import os
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    exitstatus = getattr(config, "exitstatus", 0)
    os._exit(exitstatus)
