"""Global test configuration for CORTEX test suite."""

from __future__ import annotations

import os

import pytest

os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"


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


@pytest.fixture
def skip_exergy_validation(monkeypatch):
    """Fixture to bypass exergy validation for specific tests."""
    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")


@pytest.fixture(autouse=True)
def inject_test_master_key(monkeypatch):
    """Ensure a deterministic Master Key is available for tests."""
    monkeypatch.setenv("CORTEX_TESTING", "1")
    # Base64 for 32 bytes of '0'
    monkeypatch.setenv("CORTEX_MASTER_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")

@pytest.fixture(autouse=True)
def mock_git_repo_validation(monkeypatch):
    """Prevent GitSovereignLedger from failing when CortexEngine is instantiated in tmp_path."""
    try:
        from cortex.ledger.git_ledger import GitSovereignLedger
        monkeypatch.setattr(GitSovereignLedger, "_validate_git_repo", lambda self: None)
    except ImportError:
        pass
