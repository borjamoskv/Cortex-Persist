"""Global test configuration for CORTEX test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ── Sortu scripts resolution ──────────────────────────────────────────────────
# The sortu_* modules live in scripts/sortu/. Individual test files also try to
# inject the local ~/.gemini path (for developer convenience), but CI doesn't
# have that tree.  This conftest ensures the tracked path is always present.
_SORTU_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "sortu"
if _SORTU_SCRIPTS.exists() and str(_SORTU_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SORTU_SCRIPTS))


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
