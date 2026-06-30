import os
import pytest
from babylon60.swarm.vesicular import VesicularRuntime


@pytest.fixture
def vesicle():
    return VesicularRuntime(timeout_seconds=2)


@pytest.mark.asyncio
async def test_vesicular_safe_execution(vesicle):
    payload = "print('Hello from Vesicle!')"
    success, stdout, stderr = await vesicle.execute(payload)

    assert success is True
    assert "Hello from Vesicle!" in stdout
    assert stderr == ""


@pytest.mark.asyncio
async def test_vesicular_timeout_enforcement(vesicle):
    payload = "while True: pass"
    success, stdout, stderr = await vesicle.execute(payload)

    assert success is False
    assert "TimeoutExpired" in stderr


@pytest.mark.asyncio
async def test_vesicular_env_isolation(vesicle, monkeypatch):
    # Try to read an env variable that might be set on host
    monkeypatch.setenv("SECRET_CORTEX_KEY", "DO_NOT_LEAK")

    payload = "import os; print(os.environ.get('SECRET_CORTEX_KEY', 'NOT_FOUND'))"
    success, stdout, stderr = await vesicle.execute(payload)

    assert success is True
    assert "NOT_FOUND" in stdout
    assert "DO_NOT_LEAK" not in stdout
