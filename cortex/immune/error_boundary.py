"""CORTEX v6 — Error Boundary (Ω₅ Antifragile Decorator).

Decorator + async context manager that wraps functions to auto-persist
uncaught errors as ghosts via the ErrorGhostPipeline.

Usage as decorator::

    @error_boundary("swarm.nightshift")
    async def process_crystals(self, crystals: list) -> None:
        ...  # If this raises, error → ghost pipeline automatically

Usage as context manager::

    async with ErrorBoundary("gateway.openai_spoof"):
        result = await risky_llm_call()

Both sync and async functions are supported. The decorator detects
whether the wrapped function is a coroutine and adapts accordingly.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
from typing import Any, TypeVar

logger = logging.getLogger("cortex.immune.error_boundary")

F = TypeVar("F")

# Errors that should NEVER be caught — let them propagate.
_PASSTHROUGH = (
    KeyboardInterrupt,
    SystemExit,
    GeneratorExit,
    asyncio.CancelledError,
)


class ErrorBoundary:
    """Async context manager and decorator for sovereign error capture.

    Wraps any code block to ensure uncaught exceptions are persisted
    as ghost facts via ErrorGhostPipeline, then optionally re-raised.

    Args:
        source: Identifier for the error origin (e.g. "swarm.nightshift").
        project: CORTEX project namespace. Default: "CORTEX".
        reraise: If True (default), re-raise after persisting. If False,
                 swallow the error (use for daemon loops where crash = death).
        extra_meta: Additional metadata dict merged into the ghost record.
    """

    __slots__ = ("_source", "_project", "_reraise", "_extra_meta")

    def __init__(
        self,
        source: str,
        *,
        project: str = "CORTEX",
        reraise: bool = True,
        extra_meta: dict[str, Any] | None = None,
    ) -> None:
        self._source = source
        self._project = project
        self._reraise = reraise
        self._extra_meta = extra_meta

    # ── Context Manager Protocol ──────────────────────────────────────

    async def __aenter__(self) -> ErrorBoundary:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        if exc_val is None or isinstance(exc_val, _PASSTHROUGH):
            return False

        await self._persist(exc_val)

        # Return True to suppress, False to re-raise
        return not self._reraise

    # ── Sync Context Manager ──────────────────────────────────────────

    def __enter__(self) -> ErrorBoundary:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        if exc_val is None or isinstance(exc_val, _PASSTHROUGH):
            return False

        self._persist_sync(exc_val)
        return not self._reraise

    # ── Persistence ───────────────────────────────────────────────────

    async def _persist(self, error: BaseException) -> int | None:
        """Persist error to ghost pipeline (async path)."""
        try:
            from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

            pipeline = ErrorGhostPipeline()
            fact_id = await pipeline.capture(
                error,
                source=f"boundary:{self._source}",
                project=self._project,
                extra_meta=self._extra_meta,
            )
            logger.info(
                "ErrorBoundary [%s] captured %s → ghost #%s",
                self._source,
                type(error).__qualname__,
                fact_id,
            )
            return fact_id
        except Exception as persist_err:  # noqa: BLE001
            # The boundary itself must never crash the host
            logger.error(
                "ErrorBoundary [%s] failed to persist: %s",
                self._source,
                persist_err,
            )
            return None

    def _persist_sync(self, error: BaseException) -> None:
        """Persist error to ghost pipeline (sync path)."""
        try:
            from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

            pipeline = ErrorGhostPipeline()
            pipeline.capture_sync(
                error,
                source=f"boundary:{self._source}",
                project=self._project,
                extra_meta=self._extra_meta,
            )
        except Exception as persist_err:  # noqa: BLE001
            logger.error(
                "ErrorBoundary [%s] sync persist failed: %s",
                self._source,
                persist_err,
            )


def error_boundary(
    source: str,
    *,
    project: str = "CORTEX",
    reraise: bool = True,
    extra_meta: dict[str, Any] | None = None,
) -> Any:
    """Decorator that wraps a function with an ErrorBoundary.

    Supports both sync and async functions. Detects coroutine functions
    at decoration time and wraps accordingly.

    Args:
        source: Error origin identifier (e.g. "gateway.openai").
        project: CORTEX project namespace.
        reraise: Re-raise after persisting (True) or swallow (False).
        extra_meta: Extra metadata for the ghost record.

    Example::

        @error_boundary("swarm.nightshift", reraise=False)
        async def run_cycle(self):
            ...  # errors captured, daemon stays alive
    """

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                boundary = ErrorBoundary(
                    source,
                    project=project,
                    reraise=reraise,
                    extra_meta=extra_meta,
                )
                async with boundary:
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        else:

            @functools.wraps(func)  # type: ignore[type-error]
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                boundary = ErrorBoundary(
                    source,
                    project=project,
                    reraise=reraise,
                    extra_meta=extra_meta,
                )
                with boundary:
                    return func(*args, **kwargs)  # type: ignore[type-error]

            return sync_wrapper  # type: ignore[return-value]

    return decorator
