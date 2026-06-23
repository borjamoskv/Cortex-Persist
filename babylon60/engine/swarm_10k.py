# [C5-REAL] Exergy-Maximized
"""
CORTEX-SWARM-10K Hierarchy engine.
Orchestrates L0 (SwarmCommander), L1 (LegionSupervisor), and L2 (CenturionSuperv).
Enables massive parallel scaling with deterministic O(1) properties.
"""

from __future__ import annotations

import asyncio
import collections
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from babylon60.engine.exergy_optimizer import ExergyOptimizer
from babylon60.engine.shared_bus import SovereignSharedBus
from babylon60.engine.slashing import SlashingPenalty
from babylon60.engine.ultrathink_physics import UltrathinkPhysicsEngine
from babylon60.extensions.signals.sharded_bus import ShardedAsyncSignalBus

logger = logging.getLogger("babylon60.engine.swarm_10k")


from babylon60.engine.babylon60 import Babylon60


def _to_float(v: int | float | Babylon60) -> float:
    if isinstance(v, Babylon60):
        return v.to_float()
    return float(v)


@dataclass
class NodeMetrics:
    exergy: Babylon60
    uncertainty: Babylon60
    active_children: int


class CenturionSuperv:
    """L2 Tactical Node: Handles up to 100 actual agents."""

    CAPACITY = 100

    def __init__(self, centurion_id: str, bus_name: str, tenant_id: str = "default"):
        self.id = centurion_id
        # L2 Tactical Shard: Isolated memory segment for this Centurion
        self.bus = SovereignSharedBus(name=bus_name, create=True)
        self.tenant_id = tenant_id
        self.agents: list[str] = []
        self.last_latency_ms = Babylon60(0.0)
        self.metrics = NodeMetrics(exergy=Babylon60(1.0), uncertainty=Babylon60(0.0), active_children=0)

    async def _emit_with_latency(self, **kwargs) -> int:
        start = time.perf_counter()
        res = await self.bus.emit(**kwargs)
        self.last_latency_ms = Babylon60((time.perf_counter() - start) * 1000)

        # O(1) Bit-Parallel Telemetry update (Ω₀)
        if hasattr(self.bus, "update_metrics"):
            self.bus.update_metrics(
                _to_float(self.metrics.exergy), _to_float(self.last_latency_ms), _to_float(self.metrics.uncertainty)
            )

        if self.last_latency_ms > Babylon60(32.0):
            logger.warning("VOID BREACH: %.2fms on node %s", _to_float(self.last_latency_ms), self.id)

            # Adaptive Slashing: Penalty scales with breach magnitude
            sixteen_b60 = Babylon60(16.0)
            scaling = self.last_latency_ms / sixteen_b60
            if scaling > Babylon60(20.0):
                scaling = Babylon60(20.0)
                
            dynamic_penalty = Babylon60(SlashingPenalty.MINOR_DEVIATION) * scaling
            if dynamic_penalty > Babylon60(1.0):
                dynamic_penalty = Babylon60(1.0)

            # Emit slashing signal for the governance ledger
            await self.bus.emit(
                event_type="governance:slashing",
                payload={
                    "node_id": self.id,
                    "latency_ms": _to_float(self.last_latency_ms),
                    "penalty": _to_float(dynamic_penalty),
                    "reason": f"LATENCY_BREACH ({_to_float(self.last_latency_ms):.1f}ms)",
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

    async def get_exergy(self) -> Babylon60:
        """Crystalline O(1) exergy calculation and header sync."""
        self.metrics.exergy = ExergyOptimizer.calculate_node_exergy(
            self.metrics, self.last_latency_ms, self.CAPACITY
        )
        # Mirror to SHM for L1/L0 visibility
        self.bus.update_metrics(_to_float(self.metrics.exergy), _to_float(self.last_latency_ms), _to_float(self.metrics.uncertainty))
        return self.metrics.exergy

    async def intercept_and_latent_compute(self, task: dict, semantic_space: Any) -> Any:
        """
        Intercepta la carga de la tarea antes de invocar al oráculo léxico.
        Deriva el procesamiento a Latent Thought Flow (NF-CoT).
        Se previene la generación de trazas `[THINK]` al operar directamente
        en el grafo base-60 hasta alcanzar el consenso BFT.
        """
        from babylon60.compat.optional import np

        # Dummy inicial (en producción, vendría de la capa L1_EMBEDDING del encoder)
        base_vector = np.zeros(4096, dtype=np.float32)

        # Invocamos el razonamiento continuo O(1) en memoria (RiM)
        latent_result = await semantic_space.latent_thought_flow(
            base_hidden_state=base_vector,
            session_fact_id=f"session_{self.id}",
            pulse_excitation=30.0
        )

        logger.debug(
            "Latent Thought Flow applied on node %s for task dispatch. "
            "Bypassed linguistic bottleneck.",
            self.id
        )
        return latent_result


class LegionSupervisor:
    """L1 Domain Node: Manages multiple Centurions within an isolated context."""

    def __init__(self, legion_id: str, bus: Any, tenant_id: str = "default"):
        self.id = legion_id
        self.bus = bus
        self.tenant_id = tenant_id
        self.centurions: dict[str, CenturionSuperv] = {}
        self._available_centurions: collections.deque[CenturionSuperv] = collections.deque()
        self._thermal_event = asyncio.Event()
        self._thermal_event.set()
        self.metrics = NodeMetrics(exergy=Babylon60(1.0), uncertainty=Babylon60(0.0), active_children=0)
        self._overclocked = False

    async def ensure_centurion(self) -> CenturionSuperv:
        """Find an available Centurion or spawn a new one in O(1)."""
        if self._available_centurions:
            return self._available_centurions[0]

        new_id = f"{self.id}-c{len(self.centurions)}"
        # Naming Compaction (Ω₆): Hash name to stay under 31-character POSIX limit
        shm_name = f"ctx_{hash(new_id) % 10**8}"
        new_cen = CenturionSuperv(new_id, shm_name, self.tenant_id)
        self.centurions[new_id] = new_cen
        self._available_centurions.append(new_cen)
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
        """Closed-Loop Kinetic Control: Event-based (No polling) to recover exergy."""
        if self._overclocked:
            return

        if not self.centurions:
            return

        # Calcular si la legión base tiene capacidad exergética promedio
        exergies = [c.metrics.exergy for c in self.centurions.values()]
        exergy_sum = sum(exergies, Babylon60.from_raw(0))
        exergy = exergy_sum / Babylon60(len(exergies))

        if ExergyOptimizer.is_thermally_stable(exergy):
            self._thermal_event.set()
            return

        # Bloquear Event Loop en lugar del antiguo while True: active polling (Azkartu O(1) Wait)
        self._thermal_event.clear()
        try:
            await asyncio.wait_for(self._thermal_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Thermal timeout (5s) exceeded. Forcing dispatch.")
            self._thermal_event.set()

    async def dispatch(self, task: dict) -> None:
        """Dispatch a task down the hierarchy."""
        cen = await self.ensure_centurion()
        agent_id = f"ag-{cen.id}-{len(cen.agents)}"
        await cen.deploy_agent(agent_id)

        # Azkartu Optimization: Retire full centurion in O(1)
        if len(cen.agents) >= cen.CAPACITY:
            if self._available_centurions and self._available_centurions[0] == cen:
                self._available_centurions.popleft()

        await self.bus.emit(
            event_type="task:dispatch",
            payload={"task": task, "agent_id": agent_id},
            source=self.id,
            tenant_id=self.tenant_id,
            routing_key=agent_id,
        )


class ForensicLegion(LegionSupervisor):
    """
    AX-I Forensic Legion: Specialized in contract state auditing.
    Forces zero-latency dispatch and bypasses standard exergy gates.
    """

    def __init__(self, legion_id: str, bus: Any, tenant_id: str = "default"):
        super().__init__(legion_id, bus, tenant_id)
        self._overclocked = True  # High-agency forensic agents are always hot


class SwarmCommander:
    """L0 Apex Controller: Global exergy arbitration and Legion deployment."""

    def __init__(
        self,
        bus_path: Path | str,
        tenant_id: str = "default",
        use_shm: bool = True,
    ):
        self.use_shm = use_shm
        if use_shm:
            shm_name = f"ctx_bus_{hash(str(bus_path)) % 10**8}"
            self.bus = SovereignSharedBus(name=shm_name, create=True)
        else:
            self.bus = ShardedAsyncSignalBus(base_dir=bus_path)

        self.tenant_id = tenant_id
        self.legions: dict[str, LegionSupervisor] = {}
        self._active_strike = False

    @asynccontextmanager
    async def strike_mode(self, domain: str):
        """Ω₂ Overclocking: Temporarily suspend thermal gates for a Strike."""
        legion = await self.get_or_create_legion(domain)
        original_state = legion._overclocked
        legion._overclocked = True
        logger.warning("🔱 STRIKE MODE ACTIVATED on domain: %s (Thermal Gates BYPASSED)", domain)
        try:
            yield legion
        finally:
            legion._overclocked = original_state
            logger.info("❄️ STRIKE MODE DEACTIVATED on domain: %s", domain)

    @asynccontextmanager
    async def ultrathink_horizon(
        self,
        domain: str,
        stochastic_entropy: float,
        deterministic_output: float,
        duration: float,
        deps_graph: dict,
        epicenter: str,
    ):
        """P0 Singularity Authorization: Evaluates thermodynamic budget before granting Ultrathink access."""
        radius = UltrathinkPhysicsEngine.measure_blast_radius(deps_graph, epicenter)
        authorized, msg = UltrathinkPhysicsEngine.authorize_ultrathink(
            stochastic_entropy, deterministic_output, duration, radius
        )

        if not authorized:
            logger.error("ULTRATHINK UNAUTHORIZED: %s", msg)
            raise RuntimeError(f"P0 Singularity Authorization Failed: {msg}")

        legion = await self.get_or_create_legion(domain)
        original_state = legion._overclocked
        legion._overclocked = True
        logger.critical(
            "✴️ ULTRATHINK HORIZON ACTIVATED on domain: %s (Blast Radius: %d) - %s",
            domain,
            radius,
            msg,
        )
        try:
            yield legion
        finally:
            legion._overclocked = original_state
            logger.warning(
                "❄️ ULTRATHINK HORIZON COLLAPSED on domain: %s (Exergy Stabilized)", domain
            )

    async def initialize(self) -> None:
        # Sovereign Bus v8.5 is implicitly ready upon instantiation
        if hasattr(self.bus, "initialize"):
            await self.bus.initialize()

        await self.bus.emit(
            "swarm:ignition", source="commander", tenant_id=self.tenant_id, routing_key="global"
        )

    async def get_or_create_legion(self, domain: str) -> LegionSupervisor:
        if domain not in self.legions:
            legion_id = f"legion-{domain}"
            if domain == "forensic":
                cls = ForensicLegion
            else:
                cls = LegionSupervisor

            self.legions[domain] = cls(legion_id, self.bus, self.tenant_id)
            await self.bus.emit(
                event_type="legion:spawn",
                payload={"domain": domain, "type": cls.__name__},
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
        """Purge entropy at the end of Ω_3 cycle."""
        # Signal annihilation (Unified Ω₆ interface)
        await self.bus.emit(
            "swarm:annihilation",
            source="commander",
            tenant_id=self.tenant_id,
            routing_key="global",
        )
        if isinstance(self.bus, ShardedAsyncSignalBus):
            # Shannon compaction (only for persistent bus)
            await self.bus.gc(max_age_days=0, tenant_id=self.tenant_id)

        # Cleanup L1 legions and L2 centurions to prevent shared memory leakage
        unlinked_count = 0
        closed_count = 0
        for legion in self.legions.values():
            for centurion in list(legion.centurions.values()):
                if hasattr(centurion.bus, "unlink"):
                    centurion.bus.unlink()
                    unlinked_count += 1
                elif hasattr(centurion.bus, "close"):
                    centurion.bus.close()
                    closed_count += 1
            legion.centurions.clear()
            legion._available_centurions.clear()
        logging.info(f"ANNIHILATE: Unlinked={unlinked_count}, Closed={closed_count}")

        # Lifecycle cleanup
        if isinstance(self.bus, ShardedAsyncSignalBus):
            if hasattr(self.bus, "close"):
                await self.bus.close()
        elif isinstance(self.bus, SovereignSharedBus):
            self.bus.unlink()
        elif hasattr(self.bus, "close"):
            self.bus.close()

        self.legions.clear()
