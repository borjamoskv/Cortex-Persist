# [C5-REAL] Exergy-Maximized
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
    # Epistemic Filter (AST Parse)
    try:
        tree = ast.parse(source_code)
        SovereignASTVisitor().visit(tree)
    except SyntaxError as e:
        raise SecurityViolationException(f"AST Syntax Error: {e}") from e

    # Compilation
    compiled_code = compile(tree, filename="<jit_ast>", mode="exec")

    # Isolated Execution Environment
    local_env = {}

    # We restrict __builtins__
    safe_builtins = {
        "print": print,
        "len": len,
        "range": range,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "sum": sum,
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "any": any,
        "all": all,
        "map": map,
        "filter": filter,
        "zip": zip,
        "enumerate": enumerate,
        "Exception": Exception,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        # SECURITY: __import__ deliberately excluded - CRIT-02 remediation.
        # Allowing __import__ in safe_builtins defeats the SovereignASTVisitor
        # blocklist and enables arbitrary code execution.
    }

    exec_globals = {"__builtins__": safe_builtins}
    exec_globals.update(global_ctx)

    exec(compiled_code, exec_globals, local_env)
    return local_env


def _worker(source_code: str, global_ctx: dict, result_dict: dict):
    t0 = time.perf_counter()
    result_dict["started_at"] = t0
    try:
        res = _execute_sync(source_code, global_ctx)
        # Avoid passing complex objects back via IPC
        result_dict["locals"] = list(res.keys())
        result_dict["status"] = "success"
        result_dict["exec_time_ms"] = (time.perf_counter() - t0) * 1000
    except Exception as e:
        logger.exception("[P0] Untracked Exception in SORTU JIT Executor")
        result_dict["status"] = "failed"
        result_dict["error"] = str(e)


async def run_jit_sandbox(source_code: str, timeout_ms: int = 500, global_ctx: dict = None) -> Any:  # pyright: ignore[reportArgumentType]
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
    # We allow up to 2.0 seconds for process spawn/initialization overhead
    # and strictly enforce timeout_ms on actual execution
    spawn_timeout = 2.0
    exec_timeout = timeout_ms / 1000.0

    timeout_triggered = False

    while p.is_alive():
        now = time.perf_counter()
        started_at = result_dict.get("started_at")

        if started_at is None:
            if now - start_time > spawn_timeout:
                timeout_triggered = True
                break
        else:
            if now - started_at > exec_timeout:
                timeout_triggered = True
                break

        await asyncio.sleep(0.005)

    if p.is_alive() or timeout_triggered:
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
    res_dict = dict(result_dict)

    if res_dict.get("status") == "success":
        exec_time = res_dict.get("exec_time_ms", elapsed)
        logger.info(
            "⚡ [SORTU-JIT] Sovereign AST execution complete. Yield Time: %.2fms (Process Lifetime: %.2fms)",
            exec_time,
            elapsed,
        )
        return {
            "status": "success",
            "result": {"locals": res_dict["locals"]},
            "time_ms": exec_time,
        }
    err = res_dict.get("error", "Unknown Epistemic Failure")
    logger.error("⚡ [SORTU-JIT] Epistemic failure: %s", err)
    return {"status": "failed", "error": err}
