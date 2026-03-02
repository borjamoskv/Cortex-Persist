"""CORTEX Hypervisor — Agent Handle.

The AgentHandle is the ONLY object a tenant interacts with.
3 methods. No internal types. No configuration.
If the tenant needs documentation, the architecture has failed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from cortex.hypervisor.models import HealthReport, Memory, Receipt

if TYPE_CHECKING:
    from cortex.hypervisor.core import AgencyHypervisor

__all__ = ["AgentHandle"]

logger = logging.getLogger("cortex.hypervisor.handle")


class AgentHandle:
    """The tenant's sole interface to CORTEX intelligence.

    Immutable binding to a (tenant, project) scope.
    All complexity is behind the Hypervisor membrane.

    Usage::

        handle = hypervisor.create_handle("tenant-abc", "my-project")
        receipt = await handle.remember("The release date is Q2 2026")
        memories = await handle.recall("when is the release?")
        health = await handle.reflect()
    """

    __slots__ = ("_tenant", "_project", "_hypervisor")

    def __init__(
        self,
        tenant: str,
        project: str,
        hypervisor: AgencyHypervisor,
    ) -> None:
        self._tenant = tenant
        self._project = project
        self._hypervisor = hypervisor

    @property
    def project(self) -> str:
        return self._project

    async def remember(
        self,
        content: str,
        *,
        fact_type: str = "knowledge",
        source: str | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Receipt:
        """Store a memory. Returns an opaque receipt.

        The tenant never sees: tx_id, hash_chain, embedding_vector,
        consensus_score, or any internal CORTEX field.
        """
        return await self._hypervisor._do_remember(
            tenant=self._tenant,
            project=self._project,
            content=content,
            fact_type=fact_type,
            source=source,
            tags=tags,
            meta=meta,
        )

    async def recall(
        self,
        query: str,
        *,
        limit: int = 5,
    ) -> list[Memory]:
        """Search memories by semantic similarity.

        Returns a list of Memory objects ranked by relevance.
        The tenant sees normalized relevance (0-1), not raw cosine similarity.
        """
        return await self._hypervisor._do_recall(
            tenant=self._tenant,
            project=self._project,
            query=query,
            limit=limit,
        )

    async def reflect(self) -> HealthReport:
        """Get project health status.

        The tenant sees 'healthy'/'degraded'/'critical' and 'verified'/'unverified'.
        They never see: Merkle tree depth, endocrine levels, compaction stats,
        hash-chain details, or WBFT consensus scores.
        """
        return await self._hypervisor._do_reflect(
            tenant=self._tenant,
            project=self._project,
        )

    def __repr__(self) -> str:
        return f"AgentHandle(project={self._project!r})"
