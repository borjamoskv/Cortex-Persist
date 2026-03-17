"""Global test configuration for CORTEX test suite."""

from __future__ import annotations

import asyncio
import warnings

import pytest

# Suppress Python 3.14+ deprecation warning for DefaultEventLoopPolicy
# (scheduled for removal in 3.16, but pytest-asyncio 1.3.0 requires it)
warnings.filterwarnings(
    "ignore",
    message=".*DefaultEventLoopPolicy.*",
    category=DeprecationWarning,
)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Provide event loop policy for pytest-asyncio 1.3.0 compatibility."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(autouse=True)
def mock_local_embedder(monkeypatch):
    """Mock the local embedder to prevent 10s ONNX model loads during every test."""
    class DummyEmbedder:
        def embed(self, content: str | list[str]) -> list[float] | list[list[float]]:
            if isinstance(content, str):
                return [0.0] * 768
            return [[0.0] * 768 for _ in content]
            
        async def aembed(self, content: str | list[str]) -> list[float] | list[list[float]]:
            if isinstance(content, str):
                return [0.0] * 768
            return [[0.0] * 768 for _ in content]

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

