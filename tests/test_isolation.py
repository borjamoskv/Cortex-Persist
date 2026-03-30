import asyncio

from cortex.engine.isolation import ByzantineSandbox, IsolationManager


class MockEngine:
    def __init__(self):
        self.isolation = IsolationManager(self)

def run_async(coro):
    return asyncio.run(coro)

def test_isolation_manager_creation():
    engine = MockEngine()
    manager = engine.isolation
    assert manager.engine == engine
    assert len(manager.workspaces) == 0

def test_byzantine_sandbox_execution():
    engine = MockEngine()
    sandbox = ByzantineSandbox(engine.isolation)

    # Run a simple 'echo' command to verify execution
    result_res = run_async(sandbox.execute("echo", ["hello"]))
    assert result_res.is_ok()
    result = result_res.unwrap()
    assert "hello" in result["stdout"]
    assert len(engine.isolation.workspaces) == 0

def test_byzantine_sandbox_failure():
    engine = MockEngine()
    sandbox = ByzantineSandbox(engine.isolation)

    # Non-existent command should fail
    result_res = run_async(sandbox.execute("non_existent_command_12345", []))
    assert result_res.is_err()
    assert len(engine.isolation.workspaces) == 0

def test_context_management():
    engine = MockEngine()

    async def use_context():
        async with engine.isolation.isolate() as ws:
            assert ws.id in engine.isolation.workspaces
            return ws.id

    ws_id = run_async(use_context())
    assert ws_id not in engine.isolation.workspaces
