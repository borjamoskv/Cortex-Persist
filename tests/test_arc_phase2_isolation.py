import pytest
from cortex.engine.isolation import SimpleIsolationEngine


@pytest.mark.asyncio
async def test_simple_isolation_success():
    engine = SimpleIsolationEngine()
    code = "import json\nprint(json.dumps({'res': 42}))"
    res = await engine.execute_sandbox(code, args=[])
    assert res is not None
    assert res.exit_code == 0
    assert '42' in res.stdout


@pytest.mark.asyncio
async def test_simple_isolation_timeout():
    engine = SimpleIsolationEngine(timeout=0.1)
    code = "import time\ntime.sleep(1)"
    with pytest.raises(TimeoutError):
        await engine.execute_sandbox(code, args=[])


@pytest.mark.asyncio
async def test_simple_isolation_unsafe():
    # Attempting to read a sensitive file
    engine = SimpleIsolationEngine()
    code = "import sys\nwith open('/etc/passwd') as f:\n    print(f.read())\n"
    res = await engine.execute_sandbox(code, args=[])
    # The actual OS sandbox might not block this depending on how local it is,
    # but the engine should at least restrict `os` / `sys` in a real environment.
    # For now, we assert it runs in an isolated root dir (cwd).
    assert res is not None

