# [C5-REAL] Exergy-Maximized
"""CORTEX Async Cascade Router Wrapper.

Wraps the deterministic AgentRouter with async execution,
exponential backoff, and retry logic.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from babylon60.router.router import AgentRouter

logger = logging.getLogger("cortex.router.cascade")


class AsyncCascadeRouter:
    """Async wrapper over AgentRouter with retry and exponential backoff."""

    def __init__(self, base_router: AgentRouter, max_retries: int = 3, base_delay: float = 1.0):
        self.base_router = base_router
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def route_with_retry(
        self,
        intent: str,
        context: Any = None,
        budget_remaining: float = 0.10,
        max_agents: int = 3,
    ) -> dict[str, Any]:  # type: ignore
        """
        Executes routing with exponential backoff.
        Useful for when underlying capability queries or LLM evaluations fail.
        """
        attempt = 0
        while attempt <= self.max_retries:
            try:
                # AgentRouter.route is synchronous, but we wrap it for async cascade flow
                decision = self.base_router.route(
                    intent=intent,
                    context=context,
                    budget_remaining=budget_remaining,
                    max_agents=max_agents,
                )
                logger.info("[CASCADE] Route successful on attempt %d", attempt + 1)
                return decision
            except (ValueError, KeyError, TypeError, RuntimeError) as e:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error(
                        "[CASCADE] Max retries (%d) exhausted. Routing failed: %s",
                        self.max_retries,
                        e,
                    )
                    raise

                delay = self.base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "[CASCADE] Routing failed (attempt %d). Retrying in %.1fs...", attempt, delay
                )
                await asyncio.sleep(delay)
