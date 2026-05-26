"""Global test configuration for CORTEX test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

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
    from cortex.extensions.security.anomaly_detector import DETECTOR

    DETECTOR.reset()


@pytest.fixture(autouse=True)
def inject_test_master_key(monkeypatch):
    """Ensure a deterministic Master Key is available for tests."""
    monkeypatch.setenv("CORTEX_TESTING", "1")
    # Base64 for 32 bytes of '0'
    monkeypatch.setenv("CORTEX_MASTER_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")


def pytest_configure(config):
    """Optimize pytest collection and execution on macOS."""
    import gc
    import sys

    sys.settrace(None)
    sys.setprofile(None)
    gc.freeze()


def pytest_sessionfinish(session, exitstatus):
    """Force exit to prevent finalization hangs on leaked daemon threads."""
    import os

    os._exit(exitstatus)
