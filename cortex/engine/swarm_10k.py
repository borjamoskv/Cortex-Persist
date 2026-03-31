"""
CORTEX-SWARM-10K Hierarchy engine.
Orchestrates L0 (SwarmCommander), L1 (LegionSupervisor), and L2 (CenturionSuperv).
Enables massive parallel scaling with deterministic O(1) properties.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from cortex.engine.exergy_optimizer import ExergyOptimizer
from cortex.engine.slashing import SlashingPenalty
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
        self.last_latency_ms = 0.0
        self.metrics = NodeMetrics(exergy=1.0, uncertainty=0.0, active_children=0)

    async def _emit_with_latency(self, **kwargs) -> int:
        start = time.perf_counter()
        res = await self.bus.emit(**kwargs)
        self.last_latency_ms = (time.perf_counter() - start) * 1000

        if self.last_latency_ms > 32.0:
            logger.warning("VOID BREACH: %.2fms on node %s", self.last_latency_ms, self.id)

            # Adaptive Slashing: Penalty scales with breach magnitude
            scaling = min(20.0, self.last_latency_ms / 16.0)
            dynamic_penalty = min(1.0, SlashingPenalty.MINOR_DEVIATION * scaling)

            # Emit slashing signal for the governance ledger
            await self.bus.emit(
                event_type="governance:slashing",
                payload={
                    "node_id": self.id,
                    "latency_ms": self.last_latency_ms,
                    "penalty": dynamic_penalty,
                    "reason": f"LATENCY_BREACH ({self.last_latency_ms:.1f}ms)",
                },
                source=self.id,
                tenant_id=self.tenant_id,
                routing_key="governance",
            )
        return res

    async def deploy_agent(self, agent_id: str) -> bool:
        if len(self.agents) >= self.CAPACITY:
            return False

        self.agents.append(agent_id)
        self.metrics.active_children = len(self.agents)

        await self._emit_with_latency(
            event_type="agent:spawn",
            payload={"agent_id": agent_id, "parent_node": self.id},
            source=self.id,
            tenant_id=self.tenant_id,
            routing_key=agent_id,
        )
        return True

    async def get_exergy(self) -> float:
        """Crystalline O(1) exergy calculation."""
        self.metrics.exergy = ExergyOptimizer.calculate_node_exergy(
            self.metrics, self.last_latency_ms, self.CAPACITY
        )
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
        # Selection: Pick the one with highest exergy (least agents)
        best_cen = None
        best_exergy = -1.0

        for c in self.centurions.values():
            exergy = await c.get_exergy()
            if exergy > best_exergy and len(c.agents) < c.CAPACITY:
                best_exergy = exergy
                best_cen = c

        if best_cen:
            return best_cen

        new_id = f"{self.id}-cen-{len(self.centurions)}"
        new_cen = CenturionSuperv(new_id, self.bus, self.tenant_id)
        self.centurions[new_id] = new_cen
        self.metrics.active_children = len(self.centurions)

        start = time.perf_counter()
        await self.bus.emit(
            event_type="centurion:spawn",
            payload={"centurion_id": new_id, "parent_legion": self.id},
            source=self.id,
            tenant_id=self.tenant_id,
            routing_key=self.id,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        if latency_ms > 32.0:
            logger.warning("VOID-STATE BREACH (L1): %.2fms", latency_ms)

        return new_cen

    async def wait_for_thermal_stability(self, check_interval: float = 0.01) -> None:
        """Closed-Loop Kinetic Control: Block until exergy recovers above 0.7."""
        while True:
            exergy = 1.0
            for c in self.centurions.values():
                exergy = min(exergy, await c.get_exergy())

            if ExergyOptimizer.is_thermally_stable(exergy):
                break

            # Shard is too hot. Wait for kinetic dissipation.
            await asyncio.sleep(check_interval)

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

    async def execute_global_dispatch(self, tasks: list[dict], parallel: bool = True) -> None:
        """Route massive workload across the Sharded hierarchy."""
        if parallel:
            # V7 Optimization: Bucketed Dispatch for Thermal Stability (KDF 0.05)
            await self.execute_bucketed_dispatch(tasks, bucket_size=100)
            return

        for t in tasks:
            domain = t.get("domain", "default")
            legion = await self.get_or_create_legion(domain)
            await legion.dispatch(t)

    async def execute_parallel_dispatch(self, tasks: list[dict], concurrency: int = 100) -> None:
        """High-performance parallelized signal routing (Einstein-Rosen Bridge)."""
        semaphore = asyncio.Semaphore(concurrency)

        async def _dispatch_task(task: dict):
            async with semaphore:
                domain = task.get("domain", "default")
                legion = await self.get_or_create_legion(domain)
                await legion.dispatch(task)

        await asyncio.gather(*[_dispatch_task(t) for t in tasks])

    async def execute_bucketed_dispatch(self, tasks: list[dict], bucket_size: int = 100) -> None:
        """Thermal-aware dispatch groups to prevent I/O saturation."""
        # Split 10k tasks into buckets of 100
        for i in range(0, len(tasks), bucket_size):
            bucket = tasks[i : i + bucket_size]

            # Find domain for current batch (simplification: use first task domain)
            domain = bucket[0].get("domain", "default")
            legion = await self.get_or_create_legion(domain)

            # Kinetic Feedback Throttling: Wait for Legion to cool down
            await legion.wait_for_thermal_stability()

            # Parallelize EACH bucket across its own shard set (Concurrency throttled to 50)
            await self.execute_parallel_dispatch(bucket, concurrency=50)

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
        """Purge entropy at the end of \u03a9_3 cycle."""
        await self.bus.emit(
            "swarm:annihilation", source="commander", tenant_id=self.tenant_id, routing_key="global"
        )
        # Shannon compaction
        await self.bus.gc(max_age_days=0, tenant_id=self.tenant_id)
        self.legions.clear()

        await self.bus.close()
