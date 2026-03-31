"""
CORTEX-SWARM-10K Hierarchy engine.
Orchestrates L0 (SwarmCommander), L1 (LegionSupervisor), and L2 (CenturionSuperv).
Enables massive parallel scaling with deterministic O(1) properties.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from cortex.extensions.signals.sharded_bus import ShardedAsyncSignalBus

logger = logging.getLogger("cortex.engine.swarm_10k")


@dataclass
class NodeMetrics:
    exergy: float
    uncertainty: float
    active_children: int


class CenturionSuperv:
    """L2 Tactical Node: Handles up to 100 actual agents."""

    CAPACITY = 100

    def __init__(self, centurion_id: str, bus: ShardedAsyncSignalBus, tenant_id: str = "default"):
        self.id = centurion_id
        self.bus = bus
        self.tenant_id = tenant_id
        self.agents: list[str] = []
        self.metrics = NodeMetrics(exergy=1.0, uncertainty=0.0, active_children=0)

    async def deploy_agent(self, agent_id: str) -> bool:
        if len(self.agents) >= self.CAPACITY:
            return False

        self.agents.append(agent_id)
        self.metrics.active_children = len(self.agents)

        await self.bus.emit(
            event_type="agent:spawn",
            payload={"agent_id": agent_id, "parent_node": self.id},
            source=self.id,
            tenant_id=self.tenant_id,
            routing_key=agent_id,
        )
        return True

    async def get_exergy(self) -> float:
        # Placeholder O(1) heuristic calculation
        self.metrics.exergy = max(0.0, 1.0 - (len(self.agents) / float(self.CAPACITY)))
        return self.metrics.exergy


class LegionSupervisor:
    """L1 Domain Node: Manages multiple Centurions within an isolated context."""

    def __init__(self, legion_id: str, bus: ShardedAsyncSignalBus, tenant_id: str = "default"):
        self.id = legion_id
        self.bus = bus
        self.tenant_id = tenant_id
        self.centurions: dict[str, CenturionSuperv] = {}
        self.metrics = NodeMetrics(exergy=1.0, uncertainty=0.0, active_children=0)

    async def ensure_centurion(self) -> CenturionSuperv:
        """Find an available Centurion or spawn a new one."""
        for c in self.centurions.values():
            if len(c.agents) < c.CAPACITY:
                return c

        new_id = f"{self.id}-cen-{len(self.centurions)}"
        new_cen = CenturionSuperv(new_id, self.bus, self.tenant_id)
        self.centurions[new_id] = new_cen
        self.metrics.active_children = len(self.centurions)

        await self.bus.emit(
            event_type="centurion:spawn",
            payload={"centurion_id": new_id, "parent_legion": self.id},
            source=self.id,
            tenant_id=self.tenant_id,
            routing_key=self.id,
        )
        return new_cen

    async def dispatch(self, task: dict) -> None:
        """Dispatch a task down the hierarchy."""
        cen = await self.ensure_centurion()
        agent_id = f"ag-{cen.id}-{len(cen.agents)}"
        await cen.deploy_agent(agent_id)

        await self.bus.emit(
            event_type="task:dispatch",
            payload={"task": task, "agent_id": agent_id},
            source=self.id,
            tenant_id=self.tenant_id,
            routing_key=agent_id,
        )


class SwarmCommander:
    """L0 Apex Controller: Global exergy arbitration and Legion deployment."""

    def __init__(self, bus_path: Path | str, tenant_id: str = "default"):
        self.bus = ShardedAsyncSignalBus(base_dir=bus_path)
        self.tenant_id = tenant_id
        self.legions: dict[str, LegionSupervisor] = {}

    async def initialize(self) -> None:
        await self.bus.initialize()
        await self.bus.emit(
            "swarm:ignition", source="commander", tenant_id=self.tenant_id, routing_key="global"
        )

    async def get_or_create_legion(self, domain: str) -> LegionSupervisor:
        if domain not in self.legions:
            legion_id = f"legion-{domain}"
            self.legions[domain] = LegionSupervisor(legion_id, self.bus, self.tenant_id)
            await self.bus.emit(
                event_type="legion:spawn",
                payload={"domain": domain},
                source="commander",
                tenant_id=self.tenant_id,
                routing_key=domain,
            )
        return self.legions[domain]

    async def execute_global_dispatch(self, tasks: list[dict]) -> None:
        """Route massive workload across the Sharded hierarchy."""
        for t in tasks:
            domain = t.get("domain", "default")
            legion = await self.get_or_create_legion(domain)
            await legion.dispatch(t)

    async def get_density_report(self) -> dict:
        total_legions = len(self.legions)
        total_centurions = sum(len(legion.centurions) for legion in self.legions.values())
        total_agents = sum(
            sum(len(c.agents) for c in legion.centurions.values())
            for legion in self.legions.values()
        )
        return {
            "legions": total_legions,
            "centurions": total_centurions,
            "agents": total_agents,
            "shards_active": self.bus.num_shards,
        }

    async def consolidate_and_annihilate(self) -> None:
        """Purge entropy at the end of Ω_3 cycle."""
        await self.bus.emit(
            "swarm:annihilation", source="commander", tenant_id=self.tenant_id, routing_key="global"
        )
        # Shannon compaction
        await self.bus.gc(max_age_days=0, tenant_id=self.tenant_id)
        self.legions.clear()

        await self.bus.close()
