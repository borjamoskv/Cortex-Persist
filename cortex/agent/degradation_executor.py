"""degradation_executor — sovereign_execute decorator and helpers.

Extracted from agent/degradation.py to satisfy the Landauer LOC barrier (≤500).
Contains: sovereign_execute decorator, _upgrade_to_l3, _persist_to_cortex.
All depend on the exception hierarchy and data contracts in degradation.py.
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

from cortex.agent.degradation import (
    AgentAction,
    AgentDegradedError,
    AgentResult,
    DegradationLevel,
    SchemaIncompatibilityError,
    SovereignAgentError,
)

__all__ = ["sovereign_execute", "_upgrade_to_l3", "_persist_to_cortex"]

logger = logging.getLogger("cortex.agent.degradation")

_P = ParamSpec("_P")
_R = TypeVar("_R")

_RECOVERY_DOCTOR = "Run `cortex doctor` to scan subsystem health"


def sovereign_execute(
    fallback_mode: str = "text_only",
    cortex_engine: Any | None = None,
    project: str = "default",
) -> Callable[[Callable[_P, Awaitable[_R]]], Callable[_P, Awaitable[_R]]]:
    """Decorator that wraps any agent execute() method with Sovereign Degradation.

    Implements the §14 protocol:
      1. Try full execution.
      2. On SchemaIncompatibilityError: try text-only fallback (L4).
      3. On any other SovereignAgentError: emit L3 report + re-raise.
      4. Always persist failures to CORTEX if engine is provided.
    """

    def decorator(
        fn: Callable[_P, Awaitable[_R]],
    ) -> Callable[_P, Awaitable[_R]]:
        @functools.wraps(fn)
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            t0 = time.perf_counter()
            action: AgentAction | None = next((a for a in args if isinstance(a, AgentAction)), None)

            try:
                result = await fn(*args, **kwargs)
                if isinstance(result, AgentResult):
                    result.latency_ms = (time.perf_counter() - t0) * 1000
                return result

            except SchemaIncompatibilityError as e:
                logger.warning(
                    "sovereign_execute: SchemaIncompatibility in '%s'. "
                    "Attempting L4 text-only fallback. model=%s",
                    fn.__name__,
                    e.context.get("model"),
                )
                await _persist_to_cortex(cortex_engine, project, e)

                if (
                    fallback_mode == "text_only"
                    and action is not None
                    and not action.requires_tools
                ):
                    raise AgentDegradedError(
                        cause=e, component=e.component, suggested_model=e.suggested_alt
                    ) from e

                if fallback_mode == "text_only" and action is not None:
                    degraded_action = action.as_text_only()
                    degraded_args = tuple(degraded_action if a is action else a for a in args)
                    try:
                        result = await fn(*degraded_args, **kwargs)  # type: ignore[reportCallIssue]
                        if isinstance(result, AgentResult):
                            result.latency_ms = (time.perf_counter() - t0) * 1000
                            result.degradation_level = DegradationLevel.L4_GRACEFUL
                            schema = e.context.get("required_schema")
                            result.with_warning(
                                f"Operating in text-only mode "
                                f"(tool-calling unavailable: {schema}). "
                                f"Suggested model: {e.suggested_alt}"
                            )
                        return result
                    except Exception as inner_exc:
                        raise AgentDegradedError(
                            cause=inner_exc,
                            component=e.component,
                            suggested_model=e.suggested_alt,
                        ) from inner_exc

                raise

            except SovereignAgentError as e:
                report = e.as_report()
                logger.error(
                    "sovereign_execute: L%d failure in '%s'. component=%s message=%s",
                    report.level.value,
                    fn.__name__,
                    report.component,
                    report.message,
                )
                await _persist_to_cortex(cortex_engine, project, e)
                raise

            except Exception as e:
                upgraded = AgentDegradedError(
                    cause=e,
                    component=fn.__name__,
                    recovery_steps=[
                        "Check logs for traceback",
                        _RECOVERY_DOCTOR,
                        "Isolate the failing component and retry",
                    ],
                )
                logger.error(
                    "sovereign_execute: Unknown error in '%s' upgraded to L3. original_type=%s",
                    fn.__name__,
                    type(e).__name__,
                )
                await _persist_to_cortex(cortex_engine, project, upgraded)
                raise upgraded from e

        return wrapper  # type: ignore[return-value]

    return decorator


def _upgrade_to_l3(exc: BaseException, component: str) -> AgentDegradedError:
    """Upgrade any unknown exception to L3 (Ω₅ principle)."""
    return AgentDegradedError(
        cause=exc,
        component=component,
        recovery_steps=["Check logs for traceback", _RECOVERY_DOCTOR, "Isolate and retry"],
    )


async def _persist_to_cortex(
    engine: Any | None,
    project: str,
    error: SovereignAgentError,
) -> None:
    """Attempt to persist a degradation report to CORTEX (non-blocking, never raises)."""
    if engine is None:
        return
    try:
        report = error.as_report()
        await engine.store(
            project=project,
            fact_type="error",
            content=report.to_cortex_content(),
            source="agent:degradation_protocol",
            metadata={"component": report.component, "level": report.level.value},
        )
    except Exception as persist_exc:  # noqa: BLE001
        logger.debug(
            "sovereign_execute: Failed to persist degradation report to CORTEX: %s",
            persist_exc,
        )
