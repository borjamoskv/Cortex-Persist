# [C5-REAL] Exergy-Maximized
"""
Core Execution Loop for the Ouroboros Mythos Agent.
Implements Primitive 1: Observe -> Diagnose -> Plan -> Act -> Critic -> Memorize.
"""

import asyncio
import logging
import time

from legacy_research.audit.ledger import EnterpriseAuditLedger

from .exergy_monitor import ExergyMonitor
from .mcts_planner import MCTSPlanner
from .memory_palace import MemoryPalace
from .meta_controller import MetaController
from .mythos_state import MythosState

logger = logging.getLogger(__name__)

class MythosOuroborosEngine:
    """
    Sovereign execution loop that enforces deterministic progression and 
    strictly rejects state updates if thermodynamic efficiency (Exergy) is negative.
    """

    def __init__(self, log_path: str = "security_audit_log.jsonl"):
        self.state = MythosState()
        self.memory = MemoryPalace()
        self.exergy = ExergyMonitor()
        self.meta_controller = MetaController()
        self.planner = MCTSPlanner()
        self.ledger = EnterpriseAuditLedger(log_path)
        self.is_running = False

    async def run_loop(self):
        """
        The continuous observation-action cycle.
        """
        self.is_running = True
        logger.info("[C5-REAL] Ouroboros Mythos Loop Started.")
        
        while self.is_running:
            # 1. Observe
            observation = await self._observe()
            
            # 2. Diagnose
            diagnosis = await self._diagnose(observation)
            
            # 3. Plan
            mode = self.meta_controller.decide_mode(self.exergy.current_score())
            if mode == "dream":
                logger.info("[C5-REAL] Entering Dream Mode (MCTS Forward Simulation).")
                plan = await self.planner.run_dream_simulation(diagnosis)
            else:
                plan = await self.planner.synthesize_plan(diagnosis)

            # 4. Act
            action_result = await self._act(plan)

            # 5. Critic
            critic_score = await self._criticize(action_result)

            # Check thermodynamics: Exergy yield computed purely with integers
            exergy_yield = self.exergy.compute_yield(reward=critic_score)
            
            # 6. Memorize
            if exergy_yield > 0:
                await self.memory.store_episodic(action_result, critic_score)
                self.state.commit_state_hash(action_result)
                
                # Log action deterministically in EnterpriseAuditLedger
                action_name = action_result["action_type"].decode("utf-8")
                await self.ledger.log_action(
                    tenant_id="C5-REAL-MYTHOS-1",
                    actor_role="OuroborosNode",
                    actor_id="mythos-agent-01",
                    action=action_name,
                    resource="hardware_sensors",
                    status="SUCCESS",
                    state_diff=f"exergy_yield={exergy_yield};critic_score={critic_score};cycle={self.state.cycle_count}"
                )
                logger.info(f"[C5-REAL] Action Committed. Exergy Yield: {exergy_yield}")
            else:
                logger.warning(f"[C5-REAL] Action Rejected. Negative Exergy Yield: {exergy_yield}")
                self.meta_controller.register_pain(exergy_yield)

            # Sleep using integer coordination
            await asyncio.sleep(1)

    async def _observe(self) -> dict:
        """Extracts environmental state deterministically using psutil."""
        import psutil
        try:
            cpu_pct = int(psutil.cpu_percent())
            ram_pct = int(psutil.virtual_memory().percent)
        except Exception:
            cpu_pct = 50
            ram_pct = 50

        # Deterministic base latency
        latency_ms = 45

        return {
            "timestamp_ns": time.monotonic_ns(),
            "cpu_pct_scaled": cpu_pct * 100,  # Scaled to 0-10000
            "ram_pct_scaled": ram_pct * 100,  # Scaled to 0-10000
            "latency_ms": latency_ms
        }

    async def _diagnose(self, observation: dict) -> dict:
        """Identifies anomalies and opportunities strictly via byte traces."""
        cpu = observation["cpu_pct_scaled"]
        ram = observation["ram_pct_scaled"]
        latency = observation["latency_ms"]

        diagnosis = {
            "cpu_pct_scaled": cpu,
            "ram_pct_scaled": ram,
            "latency_ms": latency,
            "anomaly": None
        }

        if cpu > 8000:
            diagnosis["anomaly"] = b"high_cpu"
        elif ram > 8000:
            diagnosis["anomaly"] = b"high_ram"
        elif latency > 100:
            diagnosis["anomaly"] = b"high_latency"

        return diagnosis

    async def _act(self, plan: dict) -> dict:
        """Executes the plan via deterministic hooks."""
        steps = plan.get("steps", [])
        if not steps:
            return {"action_type": b"noop", "status": "success"}

        primary_action = steps[0]
        action_name = primary_action.decode("utf-8")
        
        from legacy_research.extensions.ouroboros.executor import execute_plan
        status = await execute_plan({"name": action_name})

        return {
            "action_type": primary_action,
            "status": status
        }

    async def _criticize(self, action_result: dict) -> int:
        """Scores the action outcome strictly from 0 to 100."""
        from .critic_prompts import ActionCritic
        critic = ActionCritic()
        return critic.evaluate_action(action_result)

    def stop(self):
        self.is_running = False
