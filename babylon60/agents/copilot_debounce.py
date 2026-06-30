# [C5-REAL] Exergy-Maximized
"""CORTEX Level 3 Copilot - Debounce Controller.

Keystroke throttling to prevent flooding the LLM with requests.
When the human types fast, only the latest context is sent.

Pattern: coalesce → delay → fire (or cancel).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from babylon60.agents.copilot_contracts import CopilotContextPayload

logger = logging.getLogger("babylon60.agents.copilot.debounce")


class DebounceController:
    """Keystroke debouncer for copilot context requests.

    Prevents flooding the model with one request per keystroke.
    Only fires the callback after the human pauses typing.

    Behavior:
        - New context arrives → cancel previous pending, schedule new
        - Human pauses ≥ debounce_ms → fire callback with latest context
        - ESC / cursor jump → cancel_all()
        - Thread-safe via asyncio lock

    Example:
        debounce = DebounceController(debounce_ms=300)
        request_id = await debounce.schedule(context, on_context_ready)
        # If human keeps typing, previous request is auto-cancelled.
    """

    def __init__(
        self,
        *,
        debounce_ms: int = 300,
        max_pending: int = 5,
    ) -> None:
        self._debounce_s = debounce_ms / 1000.0
        self._max_pending = max_pending
        self._pending: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()
        self._latest_context: CopilotContextPayload | None = None
        self._stats = DebounceStats()

    @property
    def pending_count(self) -> int:
        """Number of pending debounced requests."""
        return len(self._pending)

    @property
    def debounce_ms(self) -> float:
        """Current debounce interval in milliseconds."""
        return self._debounce_s * 1000

    @debounce_ms.setter
    def debounce_ms(self, value: float) -> None:
        """Update debounce interval (in ms)."""
        self._debounce_s = max(50, value) / 1000.0

    async def schedule(
        self,
        context: CopilotContextPayload,
        callback: Callable[[CopilotContextPayload], Awaitable[Any]],
    ) -> str:
        """Schedule a context for deferred processing.

        If a previous request is pending, it's cancelled (coalesced).
        The callback fires after debounce_ms of silence.

        Args:
            context: Latest editor context snapshot.
            callback: Async function to call when debounce fires.

        Returns:
            Request ID for tracking/cancellation.
        """
        request_id = f"dbr-{uuid4().hex[:8]}"

        async with self._lock:
            # Cancel ALL previous pending requests (coalesce to latest)
            cancelled = self._cancel_all_locked()
            if cancelled > 0:
                self._stats.total_coalesced += cancelled
                logger.debug(
                    "Coalesced %d pending request(s), scheduling %s",
                    cancelled,
                    request_id,
                )

            self._latest_context = context
            self._stats.total_scheduled += 1

            # Schedule the deferred fire
            task = asyncio.create_task(
                self._deferred_fire(request_id, context, callback),
                name=f"debounce-{request_id}",
            )
            self._pending[request_id] = task

        return request_id

    def cancel(self, request_id: str) -> bool:
        """Cancel a specific pending request.

        Args:
            request_id: ID returned by schedule().

        Returns:
            True if request was found and cancelled.
        """
        task = self._pending.pop(request_id, None)
        if task is not None and not task.done():
            task.cancel()
            self._stats.total_cancelled += 1
            logger.debug("Cancelled debounce request: %s", request_id)
            return True
        return False

    def cancel_all(self) -> int:
        """Cancel all pending requests (e.g., on ESC or cursor jump).

        Returns:
            Number of requests cancelled.
        """
        count = 0
        for rid in list(self._pending.keys()):
            if self.cancel(rid):
                count += 1
        return count

    def get_stats(self) -> dict[str, Any]:
        """Return debounce telemetry."""
        return {
            "total_scheduled": self._stats.total_scheduled,
            "total_fired": self._stats.total_fired,
            "total_cancelled": self._stats.total_cancelled,
            "total_coalesced": self._stats.total_coalesced,
            "pending": self.pending_count,
            "fire_rate": (
                self._stats.total_fired / self._stats.total_scheduled
                if self._stats.total_scheduled > 0
                else 0.0
            ),
        }

    # ── Internal ──────────────────────────────────────────────────

    async def _deferred_fire(
        self,
        request_id: str,
        context: CopilotContextPayload,
        callback: Callable[[CopilotContextPayload], Awaitable[Any]],
    ) -> None:
        """Wait for debounce interval, then fire callback."""
        try:
            await asyncio.sleep(self._debounce_s)

            # Check if this request is still the latest
            async with self._lock:
                if request_id not in self._pending:
                    return  # Already cancelled
                del self._pending[request_id]

            # Fire the callback
            self._stats.total_fired += 1
            logger.debug("Debounce fired: %s (after %.0fms)", request_id, self.debounce_ms)
            await callback(context)

        except asyncio.CancelledError:
            logger.debug("Debounce cancelled: %s", request_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Debounce callback error: %s", exc)

    def _cancel_all_locked(self) -> int:
        """Cancel all pending tasks. Must be called under lock."""
        count = 0
        for _rid, task in list(self._pending.items()):
            if not task.done():
                task.cancel()
                count += 1
        self._pending.clear()
        return count


class DebounceStats:
    """Internal telemetry counters for the debounce controller."""

    __slots__ = ("total_cancelled", "total_coalesced", "total_fired", "total_scheduled")

    def __init__(self) -> None:
        self.total_scheduled: int = 0
        self.total_fired: int = 0
        self.total_cancelled: int = 0
        self.total_coalesced: int = 0
