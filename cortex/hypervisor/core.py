"""CORTEX Hypervisor — Core Orchestrator.

The AgencyHypervisor is the singleton that mediates between the simple
tenant surface (AgentHandle) and the fractal internal machinery.

Telescope Inversion:
  Outside → 3 verbs, 4 dataclasses
  Inside  → 68 modules, WBFT, hash-chain, endocrine, autopoiesis...
  This file is the membrane between both worlds.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from cortex.hypervisor.compressor import ComplexityCompressor
from cortex.hypervisor.handle import AgentHandle
from cortex.hypervisor.isolator import TenantIsolator
from cortex.hypervisor.models import HealthReport, Memory, Receipt
from cortex.hypervisor.projector import EventProjector

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

__all__ = ["AgencyHypervisor"]

logger = logging.getLogger("cortex.hypervisor")


class AgencyHypervisor:
    """The Telescope Membrane — singleton that hides CORTEX complexity.

    Creates AgentHandles for tenants and routes their 3 verbs
    through isolation → compression → projection pipelines.

    Usage::

        hypervisor = AgencyHypervisor(engine)
        handle = hypervisor.create_handle("tenant-abc", "my-project")
        receipt = await handle.remember("Important fact")
        memories = await handle.recall("what was important?")
        health = await handle.reflect()
    """

    __slots__ = ("_engine", "_compressor", "_projector", "_isolators")

    def __init__(self, engine: CortexEngine) -> None:
        self._engine = engine
        self._compressor = ComplexityCompressor()
        self._projector = EventProjector(engine)
        self._isolators: dict[str, TenantIsolator] = {}

    def create_handle(self, tenant: str, project: str) -> AgentHandle:
        """Create a scoped AgentHandle for a tenant+project.

        The handle is the tenant's ONLY interface.
        All complexity is hidden behind this membrane.
        """
        # Get-or-create isolator (one per tenant, O(1) lookup)
        if tenant not in self._isolators:
            self._isolators[tenant] = TenantIsolator(tenant)

        return AgentHandle(
            tenant=tenant,
            project=project,
            hypervisor=self,
        )

    # ── Internal methods called by AgentHandle ────────────────────
    # Named with underscore prefix: tenant code cannot call these
    # because they only have access to the AgentHandle.

    async def _do_remember(
        self,
        *,
        tenant: str,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        source: str | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Receipt:
        """The real remember() — store + compress + project side-effects."""
        isolator = self._isolators[tenant]

        # 1. Store via engine (isolator injects tenant_id)
        fact_id = await self._engine.store(
            **isolator.scope_kwargs(
                project=project,
                content=content,
                fact_type=fact_type,
                source=source or "hypervisor",
                tags=tags,
                meta=meta,
            ),
        )

        # 2. Fire invisible side-effects (non-blocking)
        try:
            await self._projector.on_remember(fact_id, project, content)
        except Exception:  # noqa: BLE001 — projector must never break store
            logger.debug("Projector on_remember failed for fact %d", fact_id)

        # 3. Compress to Receipt (tenant never sees fact_id as int)
        return self._compressor.to_receipt(fact_id, project)

    async def _do_recall(
        self,
        *,
        tenant: str,
        project: str,
        query: str,
        limit: int = 5,
    ) -> list[Memory]:
        """The real recall() — search + compress results."""
        isolator = self._isolators[tenant]

        # Search via engine
        results = await self._engine.search(
            **isolator.scope_kwargs(
                query=query,
                project=project,
                top_k=limit,
            ),
        )

        # Fire lightweight side-effects
        try:
            await self._projector.on_recall(query, project)
        except Exception:  # noqa: BLE001
            pass

        # Handle fuse mode returning a string instead of list
        if isinstance(results, str):
            return [
                Memory(
                    content=results,
                    relevance=1.0,
                    created=ComplexityCompressor._now()  # type: ignore[reportAttributeAccessIssue]
                    if hasattr(ComplexityCompressor, "_now")
                    else __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                    source="fusion",
                )
            ]

        # Compress SearchResults → Memory objects
        return [self._compressor.search_result_to_memory(r) for r in results[:limit]]

    async def _do_reflect(
        self,
        *,
        tenant: str,
        project: str,
    ) -> HealthReport:
        """The real reflect() — gather stats + verify chain + compress."""
        isolator = self._isolators[tenant]
        tid = isolator.tenant_id

        # Gather internal stats
        try:
            facts = await self._engine.recall(
                project=project,
                tenant_id=tid,
                limit=1,
            )
            active_count = len(facts)

            # Get full stats for count
            stats = await self._engine.stats()
            active_count = stats.get("active_facts", active_count)

            last_activity = facts[0].created_at if facts else None
        except Exception:  # noqa: BLE001
            active_count = 0
            last_activity = None

        # Verify ledger integrity
        chain_valid = True
        try:
            if hasattr(self._engine, "verify_ledger"):
                result = await self._engine.verify_ledger()
                chain_valid = (
                    result.get("valid", True) if isinstance(result, dict) else bool(result)
                )
        except Exception:  # noqa: BLE001
            chain_valid = False

        # Compress to HealthReport
        return self._compressor.to_health_report(
            active_count=active_count,
            last_activity_iso=last_activity,
            chain_valid=chain_valid,
        )
