# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX LLM Router — Hedged Request Strategy.

DNS-over-HTTPS pattern: race-to-first parallel execution.
Sends query to N providers simultaneously, takes the first Ok response,
cancels the rest.

Extraído de router.py (Ω₂ Landauer split).
"""

from __future__ import annotations
from typing import Optional

import asyncio
import logging
import time

from cortex.extensions.llm._models import BaseProvider, CortexPrompt, HedgedResult

__all__ = ["HedgedRequestStrategy"]

logger = logging.getLogger("cortex.extensions.llm.hedging")


class HedgedRequestStrategy:
    """DNS-over-HTTPS inspired race-to-first execution.

    Sends the same query to N providers simultaneously via
    ``asyncio.wait(FIRST_COMPLETED)``. Takes the first Ok response,
    cancels the rest. If all fail, returns the collected errors so
    the caller can fall through to the sequential cascade.

    Axiom: Ω₂ (controlled waste < latency) + Ω₅ (redundancy as fuel).
    """

    @classmethod
    async def race(
        cls,
        providers: list[BaseProvider],
        prompt: CortexPrompt,
    ) -> tuple[Optional[HedgedResult], list[str]]:
        """Race N providers simultaneously. Returns (winner | None, errors).

        DNS-over-HTTPS pattern: query sent to all providers concurrently,
        first valid response wins, all others are cancelled.

        Returns:
            (HedgedResult, [])       — winner found, errors empty.
            (None, ["p: reason", …]) — all failed, caller falls to cascade.
        """
        if not providers:
            return None, ["No providers for hedging"]

        start = time.monotonic()
        tasks: dict[asyncio.Task[str], BaseProvider] = {
            asyncio.create_task(p.invoke(prompt), name=f"hedge:{p.provider_name}"): p
            for p in providers
        }
        all_tasks = set(tasks)  # immutable snapshot — pending mutates in loop
        pending: set[asyncio.Task[str]] = set(tasks)
        errors: list[str] = []

        try:
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for completed in done:
                    provider = tasks[completed]
                    exc = completed.exception()
                    if exc is not None:
                        errors.append(f"{provider.provider_name}: {exc}")
                        logger.debug(
                            "Hedge loser (error): %s — %s",
                            provider.provider_name,
                            exc,
                        )
                        continue

                    # Winner — capture latency, cancel remaining
                    latency_ms = (time.monotonic() - start) * 1000
                    cancelled_names: list[str] = []
                    for loser in pending:
                        loser.cancel()
                        cancelled_names.append(tasks[loser].provider_name)

                    result = HedgedResult(
                        winner=provider.provider_name,
                        response=completed.result(),
                        latency_ms=latency_ms,
                        cancelled=tuple(cancelled_names),
                    )
                    logger.info(
                        "Hedge winner: %s (%.1fms) | cancelled: %s",
                        result.winner,
                        result.latency_ms,
                        cancelled_names or "none",
                    )
                    return result, []

            # All tasks completed with errors
            return None, errors

        except asyncio.CancelledError:
            raise  # propagate — caller owns the event loop context
        except (RuntimeError, ValueError, TypeError, OSError) as exc:
            errors.append(f"Hedging infrastructure: {exc}")
            return None, errors
        finally:
            # Guaranteed cleanup using the immutable snapshot (Ω₃ Byzantine Default)
            # `pending` may have been reassigned mid-loop — all_tasks is the safe ref
            for t in all_tasks:
                if not t.done():
                    t.cancel()
            # Suppress ResourceWarnings from cancelled tasks
            for t in all_tasks:
                if not t.done():
                    try:
                        await t
                    except (asyncio.CancelledError, Exception):  # noqa: BLE001
                        pass
