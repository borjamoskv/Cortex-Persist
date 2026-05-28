"""pytest configuration for cortex/agents/ tests."""


def pytest_configure(config: object) -> None:
    """Register asyncio marker for the agents test suite."""
    config.addinivalue_line(  # type: ignore[union-attr]
        "markers",
        "asyncio: mark test as async",
    )
