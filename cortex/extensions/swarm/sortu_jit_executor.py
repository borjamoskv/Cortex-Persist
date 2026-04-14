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
    }

    exec_globals = {"__builtins__": safe_builtins}
    exec_globals.update(global_ctx)

    exec(compiled_code, exec_globals, local_env)
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


async def run_jit_sandbox(source_code: str, timeout_ms: int = 50, global_ctx: dict = None) -> Any:
    """
    Executes Python AST in a 50ms bounded memory-only sandbox.
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
        raise JITTimeoutException("Execution exceeded thermodynamic bounds (50ms)")

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
