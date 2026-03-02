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
