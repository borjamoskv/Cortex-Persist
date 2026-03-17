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
    # Skip thermodynamic exergy validation in tests — unit tests don't provide
    # real prior/posterior entropy metadata and should not be gated by Ω₁₃.
    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")


@pytest.fixture(autouse=True)
def reset_store_mixin_thermo_state():
    """Reset StoreMixin class-level thermodynamic state between tests.

    _agent_mode and _thermo_counters are ClassVars — they persist across
    test instances and can cause DECORATIVE mode to bleed into subsequent
    tests if a prior test triggers the thermodynamic waste threshold.
    """
    from cortex.engine.store_mixin import StoreMixin
    from cortex.guards.thermodynamic import AgentMode, ThermodynamicCounters

    # Reset before each test
    StoreMixin._agent_mode = AgentMode.ACTIVE
    StoreMixin._thermo_counters = ThermodynamicCounters()
    StoreMixin._thermal_decay_cache = {}
    yield
    # Reset after each test to leave a clean slate
    StoreMixin._agent_mode = AgentMode.ACTIVE
    StoreMixin._thermo_counters = ThermodynamicCounters()
    StoreMixin._thermal_decay_cache = {}
