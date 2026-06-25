# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import os
import sys
import importlib
from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from pathlib import Path


# Set environment variables for tests globally before any imports/fixtures run
os.environ["CORTEX_TESTING"] = "1"
os.environ["CORTEX_NO_OMEGA"] = "1"
os.environ["CORTEX_MASTER_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"

# Dynamically inject legacy skill modules moved to ANTI_GRAVITY/01_ACTIVE during reorganization
import importlib.util
import types
def _inject_legacy_skill_modules():
    _REPO_ROOT = Path(__file__).resolve().parents[1]
    
    # Create dummy skills module
    skills = types.ModuleType("skills")
    sys.modules["skills"] = skills
    
    mappings = {
        "skills.registry": _REPO_ROOT / "ANTI_GRAVITY" / "01_ACTIVE" / "observability" / "registry.py",
        "skills.deploy": _REPO_ROOT / "ANTI_GRAVITY" / "01_ACTIVE" / "memory" / "deploy.py",
        "skills.repo_health": _REPO_ROOT / "ANTI_GRAVITY" / "01_ACTIVE" / "creation" / "repo_health.py",
    }
    
    for mod_name, filepath in mappings.items():
        if filepath.exists():
            spec = importlib.util.spec_from_file_location(mod_name, str(filepath))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = module
                spec.loader.exec_module(module)

_inject_legacy_skill_modules()

import pytest

# ── Repo-local import resolution ──────────────────────────────────────────────
# Several legacy tests import modules that live outside the installed package
# surface. Resolve them relative to the checkout so CI doesn't depend on a
# developer-specific home directory layout.
_REPO_ROOT = Path(__file__).resolve().parents[1]
# Prepend repo root to ensure local code takes priority over installed package
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

for extra_path in (
    _REPO_ROOT / "cortex-core",
    _REPO_ROOT / "scripts" / "sortu",
    _REPO_ROOT / "legacy_research" / "extensions",
    _REPO_ROOT / "ANTI_GRAVITY" / "01_ACTIVE" / "memory",
    _REPO_ROOT / "ANTI_GRAVITY" / "01_ACTIVE" / "memory" / "lab",
    _REPO_ROOT / "ANTI_GRAVITY" / "01_ACTIVE" / "memory" / "sortu",
    _REPO_ROOT / "ANTI_GRAVITY" / "01_ACTIVE" / "creation",
    _REPO_ROOT / "ANTI_GRAVITY" / "01_ACTIVE" / "creation" / "sortu",
    _REPO_ROOT / "ANTI_GRAVITY" / "01_ACTIVE" / "unknown" / "sortu",
):
    if extra_path.exists() and str(extra_path) not in sys.path:
        sys.path.append(str(extra_path))


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
    from cortex.extensions.security.anomaly_detector import DETECTOR

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
    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")

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
