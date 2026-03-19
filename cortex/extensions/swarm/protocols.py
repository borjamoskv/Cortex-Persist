"""
Swarm Protocols — CORTEX Swarm Micro-Kernel Interfaces.
[Ariadne-Arch-Omega — ADR-035]
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SwarmExtension(Protocol):
    """Base protocol for all swarm extension modules."""

    def get_status(self) -> dict[str, Any]: ...

    def evict_stale_data(self) -> int:
        """Standard method for entropy cleanup (Ciclo 5 compliant)."""
        ...


class SwarmModule(Protocol):
    """Refined protocol for pluggable swarm logic units."""

    name: str

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...
