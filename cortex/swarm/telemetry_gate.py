"""
Sovereign Telemetry Gate (RADAR-Ω + KETER-OMEGA)
================================================
Axiom: "Un swarm que no puede trazar probabilísticamente las decisiones
de sus nodos es una bomba estocástica."

Quality gate — NOT a dashboard.  If the evaluator scores an LLM output
below threshold, the transaction is aborted *before* it can poison CORTEX
memory.  Traces are emitted to LangSmith for post-mortem, but the runtime
decision is fully local and O(1).

Changelog v2 — 2026-03-09:
  ✓ Aligned with real Result monad (Ok/Err, not Result.fail)
  ✓ Async-native gate (sovereign_quality_gate_async)
  ✓ Circuit breaker: consecutive failures -> hard-kill without retrying
  ✓ Evaluator composition (AND/OR chains)
  ✓ PII redaction uses allowlist instead of denylist
  ✓ Latency telemetry per gate invocation
  ✓ Integration point with CapatazOrchestrator (SovereignReward feedback)
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeAlias, TypeVar

from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline
from cortex.utils.result import Err, Result

# Optional LangSmith — graceful degradation, never a hard dep
try:
    from langsmith.run_trees import RunTree

    _HAS_LANGSMITH = True
except ImportError:  # pragma: no cover
    _HAS_LANGSMITH = False
    RunTree = None  # type: ignore[assignment,misc]

logger = logging.getLogger("cortex.swarm.telemetry_gate")

T = TypeVar("T")

# ── Allowlist for safe kwarg keys to send to traces ────────────────────
_SAFE_KWARG_PREFIXES = frozenset(
    {"query", "prompt", "model", "temperature", "max_tokens", "tool", "agent", "name"}
)


# Evaluator signature: (inputs: dict, output: Any) -> float [0.0 – 1.0]
EvaluatorFn: TypeAlias = Callable[[dict[str, Any], Any], float]


# ═════════════════════════════════════════════════════════════════════════
#  Exceptions
# ═════════════════════════════════════════════════════════════════════════


class StochasticDetonationError(Exception):
    """LLM output failed the Sovereign Quality Gate."""

    def __init__(self, tool_name: str, score: float, threshold: float) -> None:
        self.tool_name = tool_name
        self.score = score
        self.threshold = threshold
        super().__init__(
            f"💣 DETONATION [{tool_name}]: score {score:.3f} < threshold {threshold:.3f}"
        )


class CircuitOpenError(Exception):
    """Gate tripped the circuit breaker after consecutive failures."""

    def __init__(self, tool_name: str, failures: int) -> None:
        self.tool_name = tool_name
        self.failures = failures
        super().__init__(
            f"🔌 CIRCUIT OPEN [{tool_name}]: {failures} consecutive failures — refusing execution"
        )


# ═════════════════════════════════════════════════════════════════════════
#  Tracing Bootstrap
# ═════════════════════════════════════════════════════════════════════════


def init_sovereign_tracing(project_name: str = "cortex-master-swarm") -> None:
    """Force-enable LangSmith tracing.  Idempotent."""
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_PROJECT"] = project_name
    logger.info("RADAR-Ω: Tracing active → project=%s", project_name)


# ═════════════════════════════════════════════════════════════════════════
#  Core: Evaluator Protocol & Combinators
# ═════════════════════════════════════════════════════════════════════════

# NOTE: EvaluatorFn type alias defined above (line 54)


def exact_match_evaluator(expected_keys: list[str]) -> EvaluatorFn:
    """Score 1.0 if output dict contains ALL expected keys, else 0.0."""

    def _eval(inputs: dict[str, Any], output: Any) -> float:
        if not isinstance(output, dict):
            return 0.0
        missing = [k for k in expected_keys if k not in output]
        if missing:
            logger.debug("exact_match: missing keys %s", missing)
            return 0.0
        return 1.0

    return _eval


def confidence_evaluator(field: str = "confidence", min_val: float = 0.7) -> EvaluatorFn:
    """Score based on a numeric confidence field inside the output dict."""

    def _eval(_inputs: dict[str, Any], output: Any) -> float:
        if not isinstance(output, dict):
            return 0.0
        val = output.get(field)
        if not isinstance(val, (int, float)):
            return 0.0
        return 1.0 if val >= min_val else float(val / min_val)

    return _eval


def compose_and(*evaluators: EvaluatorFn) -> EvaluatorFn:
    """All evaluators must pass — returns the minimum score."""

    def _eval(inputs: dict[str, Any], output: Any) -> float:
        return min(ev(inputs, output) for ev in evaluators)

    return _eval


def compose_or(*evaluators: EvaluatorFn) -> EvaluatorFn:
    """At least one evaluator must pass — returns the maximum score."""

    def _eval(inputs: dict[str, Any], output: Any) -> float:
        return max(ev(inputs, output) for ev in evaluators)

    return _eval


# ═════════════════════════════════════════════════════════════════════════
#  Circuit Breaker State (per tool_name, in-process)
# ═════════════════════════════════════════════════════════════════════════

_circuit_state: dict[str, int] = {}  # tool_name → consecutive failures
_CIRCUIT_BREAKER_LIMIT = 3


def _circuit_record_success(tool_name: str) -> None:
    _circuit_state.pop(tool_name, None)


def _circuit_record_failure(tool_name: str) -> int:
    count = _circuit_state.get(tool_name, 0) + 1
    _circuit_state[tool_name] = count
    return count


def _circuit_is_open(tool_name: str) -> bool:
    return _circuit_state.get(tool_name, 0) >= _CIRCUIT_BREAKER_LIMIT


def circuit_reset(tool_name: str) -> None:
    """Manually reset circuit breaker for a tool (e.g. after config fix)."""
    _circuit_state.pop(tool_name, None)
    logger.info("Circuit breaker reset for %s", tool_name)


# ═════════════════════════════════════════════════════════════════════════
#  PII-safe kwargs extractor (allowlist, not denylist)
# ═════════════════════════════════════════════════════════════════════════


def _sanitize_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Only forward keys whose prefix is in the allowlist."""
    return {
        k: v
        for k, v in kwargs.items()
        if any(k.lower().startswith(prefix) for prefix in _SAFE_KWARG_PREFIXES)
    }


# ═════════════════════════════════════════════════════════════════════════
#  Sync Gate Decorator
# ═════════════════════════════════════════════════════════════════════════


def sovereign_quality_gate(
    tool_name: str,
    evaluator: EvaluatorFn | None = None,
    threshold: float = 0.8,
) -> Callable:
    """
    Synchronous quality gate decorator.

    Wraps a function that returns ``Ok[T] | Err[E]``.
    1. Checks circuit breaker — refuses execution if open.
    2. Executes the function.
    3. On Ok: runs evaluator; if score < threshold → Err + detonation.
    4. Emits LangSmith trace with latency + score metadata.
    """

    def decorator(func: Callable[..., Result]) -> Callable[..., Result]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Result:
            # ── Circuit breaker check ──────────────────────────────
            if _circuit_is_open(tool_name):
                err = CircuitOpenError(tool_name, _CIRCUIT_BREAKER_LIMIT)
                logger.error(str(err))
                return Err(str(err))

            t0 = time.monotonic()
            run_tree = _maybe_create_run_tree(tool_name, args, kwargs)

            try:
                result = func(*args, **kwargs)
            except (TypeError, ValueError, KeyError, AttributeError, RuntimeError) as exc:
                elapsed = time.monotonic() - t0
                _circuit_record_failure(tool_name)
                _end_run_tree(run_tree, error=str(exc), latency_ms=elapsed * 1000)
                logger.exception("Gate [%s]: unhandled exception", tool_name)
                # 150/100: Capture in ghost pipeline
                ErrorGhostPipeline().capture_sync(
                    exc, source=f"gate:sync:{tool_name}", project="CORTEX_SWARM"
                )
                return Err(f"{type(exc).__name__}: {exc}")

            elapsed = time.monotonic() - t0
            return _evaluate_and_finalize(
                tool_name, evaluator, threshold, result, kwargs, run_tree, elapsed
            )

        return wrapper

    return decorator


# ═════════════════════════════════════════════════════════════════════════
#  Async Gate Decorator
# ═════════════════════════════════════════════════════════════════════════


def sovereign_quality_gate_async(
    tool_name: str,
    evaluator: EvaluatorFn | None = None,
    threshold: float = 0.8,
) -> Callable:
    """Async variant — wraps ``async def fn(...) -> Result``."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Result:
            if _circuit_is_open(tool_name):
                err = CircuitOpenError(tool_name, _CIRCUIT_BREAKER_LIMIT)
                logger.error(str(err))
                return Err(str(err))

            t0 = time.monotonic()
            run_tree = _maybe_create_run_tree(tool_name, args, kwargs)

            try:
                result = await func(*args, **kwargs)
            except (TypeError, ValueError, KeyError, AttributeError, RuntimeError) as exc:
                elapsed = time.monotonic() - t0
                _circuit_record_failure(tool_name)
                _end_run_tree(run_tree, error=str(exc), latency_ms=elapsed * 1000)
                logger.exception("Gate [%s]: unhandled exception (async)", tool_name)
                # 150/100: Capture in ghost pipeline
                await ErrorGhostPipeline().capture(
                    exc, source=f"gate:async:{tool_name}", project="CORTEX_SWARM"
                )
                return Err(f"{type(exc).__name__}: {exc}")

            elapsed = time.monotonic() - t0
            return _evaluate_and_finalize(
                tool_name, evaluator, threshold, result, kwargs, run_tree, elapsed
            )

        return wrapper

    return decorator


# ═════════════════════════════════════════════════════════════════════════
#  Shared internals
# ═════════════════════════════════════════════════════════════════════════


def _maybe_create_run_tree(tool_name: str, args: tuple, kwargs: dict[str, Any]) -> Any | None:
    """Create a LangSmith RunTree if the SDK is available and configured."""
    if not _HAS_LANGSMITH or not os.getenv("LANGCHAIN_API_KEY"):
        return None
    try:
        rt = RunTree(  # type: ignore[misc]
            name=f"sovereign_gate:{tool_name}",
            run_type="chain",
            inputs={"args": repr(args)[:500], "kwargs": _sanitize_kwargs(kwargs)},
            project_name=os.getenv("LANGCHAIN_PROJECT", "cortex-master-swarm"),
        )
        rt.post()
        return rt
    except (ImportError, ValueError, RuntimeError):
        logger.debug("RunTree creation failed — continuing without trace", exc_info=True)
        return None


def _end_run_tree(
    run_tree: Any | None,
    *,
    outputs: dict[str, Any] | None = None,
    error: str | None = None,
    latency_ms: float = 0.0,
) -> None:
    """Safely close a RunTree (no-op if None)."""
    if run_tree is None:
        return
    try:
        extra = {"latency_ms": round(latency_ms, 2)}
        if error:
            run_tree.end(error=error, outputs=extra)
        else:
            run_tree.end(outputs={**(outputs or {}), **extra})
        run_tree.patch()
    except (AttributeError, ValueError, TypeError) as rt_end_err:
        logger.debug("RunTree finalization failed: %s", rt_end_err)


def _evaluate_and_finalize(
    tool_name: str,
    evaluator: EvaluatorFn | None,
    threshold: float,
    result: Result,
    kwargs: dict[str, Any],
    run_tree: Any | None,
    elapsed_s: float,
) -> Result:
    """Score the result, update circuit breaker, emit trace."""
    latency_ms = elapsed_s * 1000

    # ── Inner Result already failed ────────────────────────────────
    if isinstance(result, Err):
        _circuit_record_failure(tool_name)
        _end_run_tree(run_tree, error=repr(result.error), latency_ms=latency_ms)
        return result

    # ── Unwrap Ok value ────────────────────────────────────────────
    output_val = result.value  # type: ignore[union-attr]

    # ── Evaluate ───────────────────────────────────────────────────
    score = 1.0
    if evaluator is not None:
        try:
            score = evaluator(kwargs, output_val)
        except (TypeError, ValueError, KeyError, AttributeError) as eval_exc:
            logger.warning("Evaluator crashed for [%s]: %s", tool_name, eval_exc)
            # 150/100: Evaluator crash is a high-entropy event
            ErrorGhostPipeline().capture_sync(
                eval_exc, source=f"gate:evaluator:{tool_name}", project="CORTEX_SWARM"
            )
            score = 0.0

    if score < threshold:
        _circuit_record_failure(tool_name)
        det = StochasticDetonationError(tool_name, score, threshold)
        logger.error(str(det))
        _end_run_tree(run_tree, error=str(det), latency_ms=latency_ms)
        return Err(str(det))

    # ── Success path ───────────────────────────────────────────────
    _circuit_record_success(tool_name)
    _end_run_tree(
        run_tree,
        outputs={"score": round(score, 4), "output_type": type(output_val).__name__},
        latency_ms=latency_ms,
    )
    logger.debug("Gate [%s] PASSED: score=%.3f latency=%.1fms", tool_name, score, latency_ms)
    return result
