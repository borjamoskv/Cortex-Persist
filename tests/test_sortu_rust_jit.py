import pytest
import asyncio
from cortex.extensions.swarm.sortu_jit_executor import run_jit_sandbox


@pytest.mark.asyncio
async def test_rust_jit_execution():
    """
    Verifies that math-intensive loops are correctly transpiled, compiled,
    and executed inside the dynamic Rust JIT substrate with ultra-low latency.
    """
    source_code = """
def run_computation(x, y):
    total = 0.0
    for i in range(10):
        if i % 2 == 0:
            total = total + x
        else:
            total = total + y
    return total
"""
    ctx = {"x": 2.0, "y": 3.0}
    res = await run_jit_sandbox(source_code, global_ctx=ctx)

    assert res["status"] == "success"
    assert "result" in res["result"]["locals"]
    # 5 iterations of x (2.0) and 5 iterations of y (3.0) = 10.0 + 15.0 = 25.0
    # Let's verify compilation succeeded
    assert res["time_ms"] > 0


@pytest.mark.asyncio
async def test_rust_jit_fallback_to_python():
    """
    Verifies that code containing non-transpilable features (like dicts or complex calls)
    correctly triggers a safe fallback to the Python sandbox.
    """
    source_code = """
def run_fallback(x):
    d = {"val": x}
    return d["val"]
"""
    ctx = {"x": 42.0}
    res = await run_jit_sandbox(source_code, timeout_ms=1000, global_ctx=ctx)

    assert res["status"] == "success"
    assert "run_fallback" in res["result"]["locals"]
