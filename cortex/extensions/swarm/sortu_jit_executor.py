import ast
import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger("cortex.autodidact.sandbox")
logging.basicConfig(level=logging.INFO)


class SecurityViolationException(Exception):
    pass


class JITTimeoutException(Exception):
    pass


class SovereignASTVisitor(ast.NodeVisitor):
    def visit_Import(self, node):
        for name in node.names:
            if name.name in ["os", "sys", "subprocess", "shlex", "builtins"]:
                raise SecurityViolationException(f"Forbidden import: {name.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module in ["os", "sys", "subprocess", "shlex", "builtins"]:
            raise SecurityViolationException(f"Forbidden import from module: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in ["open", "eval", "exec", "input", "breakpoint", "__import__"]:
                raise SecurityViolationException(f"Forbidden call: {node.func.id}")
        self.generic_visit(node)


def _execute_sync(source_code: str, global_ctx: dict) -> dict:
    from cortex.utils.sandbox import ASTSandbox
    
    sandbox = ASTSandbox(timeout_seconds=2)
    exec_result = sandbox.safe_exec(source_code)
    
    if not exec_result.success:
        raise SecurityViolationException(f"AST Sandbox Error: {exec_result.error}")
        
    local_env = exec_result.output
    # Inject global context if needed
    for k, v in global_ctx.items():
        if k not in local_env:
            local_env[k] = v
            
    return local_env


def _worker(source_code: str, global_ctx: dict, result_dict: dict):
    try:
        res = _execute_sync(source_code, global_ctx)
        # Avoid passing complex objects back via IPC
        result_dict["locals"] = list(res.keys())
        result_dict["status"] = "success"
    except Exception as e:
        result_dict["status"] = "failed"
        result_dict["error"] = str(e)


async def run_jit_sandbox(source_code: str, timeout_ms: int = 500, global_ctx: dict = None) -> Any:
    """
    Executes Python AST in a bounded memory-only sandbox.
    Uses multiprocessing to guarantee true OS-level termination and bypass GIL deadlocks.
    """
    ctx = global_ctx or {}
    start_time = time.perf_counter()

    import multiprocessing

    manager = multiprocessing.Manager()
    result_dict = manager.dict()

    # Run in a completely separate process to protect the main node
    p = multiprocessing.Process(target=_worker, args=(source_code, ctx, result_dict))
    p.start()

    # Await in a non-blocking way to keep event loop alive
    # We poll every 5ms up to timeout_ms
    max_iters = timeout_ms // 5
    iters = 0
    while p.is_alive() and iters < max_iters:
        await asyncio.sleep(0.005)
        iters += 1

    if p.is_alive():
        p.terminate()
        p.join(timeout=0.1)
        if p.is_alive():
            p.kill()  # OS-level SIGKILL

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.error(
            "⚡ [SORTU-JIT] Thermodynamic Timeout triggered (%.2fms). Process terminated via SIGKILL.",
            elapsed,
        )
        raise JITTimeoutException(f"Execution exceeded thermodynamic bounds ({timeout_ms}ms)")

    elapsed = (time.perf_counter() - start_time) * 1000

    if dict(result_dict).get("status") == "success":
        logger.info("⚡ [SORTU-JIT] Sovereign AST execution complete. Yield Time: %.2fms", elapsed)
        return {
            "status": "success",
            "result": {"locals": result_dict["locals"]},
            "time_ms": elapsed,
        }
    else:
        err = dict(result_dict).get("error", "Unknown Epistemic Failure")
        logger.error("⚡ [SORTU-JIT] Epistemic failure: %s", err)
        return {"status": "failed", "error": err}
