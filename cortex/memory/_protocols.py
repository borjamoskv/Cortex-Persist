# [C5-REAL] Exergy-Maximized
from typing import Protocol, Any
from cortex.memory.models import MemoryEvent


class CortexMemoryManagerProtocol(Protocol):
    """Protocol defining the interface for the Cortex Memory Manager.

    Defines primary APIs for processing interaction, context assembly, nrem consolidation,
    and factual storage across tripartite layers.
    """

    _hdc: Any
    _hologram: Any
    _dynamic_space: Any
    _l2: Any
    metamemory: Any
    _encoder: Any
    _schema_engine: Any

    async def process_interaction(
        self,
        role: str,
        content: str,
        session_id: str,
        token_count: int,
        tenant_id: str | None = None,
        project_id: str = "default_project",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEvent:
        """Processes and appends an interaction to Working Memory (L1) and Ledger (L3)."""
        ...

    async def store(
        self,
        tenant_id: str | None = None,
        project_id: str = "default",
        content: str = "",
        fact_type: str = "general",
        metadata: dict[str, Any] | None = None,
        layer: str = "semantic",
        parent_decision_id: str | int | None = None,
        use_bus: bool = False,
    ) -> str:
        """Stores a fact directly in Vector Store (L2) with metadata and type."""
        ...

    async def assemble_context(
        self,
        tenant_id: str | None = None,
        project_id: str = "default",
        query: str | None = None,
        max_episodes: int = 3,
        fuse_context: bool = False,
        layer: str | None = None,
    ) -> dict[str, Any]:
        """Assembles working and episodic context, optionally applying fusion."""
        ...

    async def nrem_consolidation(self, tenant_id: str, project_id: str | None = None) -> dict:
        """Runs the NREM consolidation cycle, optimizing semantic and episodic vectors."""
        ...

