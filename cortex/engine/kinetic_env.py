"""
CORTEX Kinetic Environment (Ω-Architecture).

Implements AX-044 (Kinetic Intelligence) and AX-043 (Induction over Iteration).
This environment wraps the Isolation Manager, Maxwell (Exergy), Chaos (Immunity),
and the Cryptographic Ledger. It provides a Gymnasium-like interactive loop
for measuring intelligent swarm agents acting with real thermodynamic friction.
"""

import asyncio
import time
import logging
from typing import Any, Dict

from cortex.engine.isolation import IsolationManager, IsolationLevel
from cortex.daemon.maxwell import MaxwellDaemon
from cortex.daemon.chaos import ChaosDaemon
from cortex.ledger.event_ledger import get_default_ledger
from cortex.utils.result import Ok

logger = logging.getLogger("cortex.engine.kinetic_env")


class KineticEnv:
    """
    Sovereign Evaluation Environment.
    State is mutable across episodes. Intelligent agents must navigate
    with quantifiable Exergy and Chaos resilience.
    """

    def __init__(self, tenant_id: str = "default", level: IsolationLevel = IsolationLevel.LOCAL):
        self.tenant_id = tenant_id
        self.level = level
        self.isolation = IsolationManager()
        self.maxwell = MaxwellDaemon(engine=self)
        self.chaos = ChaosDaemon(engine=self)
        self.ledger = get_default_ledger()
        
        self.sandbox = None
        self.episode_id = None
        self.step_count = 0

    async def reset(self) -> Dict[str, Any]:
        """Reset the environment, clearing isolation and spawning a new one."""
        self.episode_id = f"ep_{int(time.time())}"
        self.step_count = 0

        # Terminate old sandbox if persists
        if self.sandbox:
            await self.isolation.destroy_workspace(self.sandbox.workspace_id)
            self.sandbox = None

        res = await self.isolation.create_workspace(level=self.level, project=self.episode_id)
        if not isinstance(res, Ok):
            raise RuntimeError(f"Failed to provision kinetic workspace: {res}")
            
        import cortex.engine.isolation
        self.sandbox = cortex.engine.isolation.ByzantineSandbox(self.isolation, res.value.id)
        
        await self.chaos.start()
        
        await self.ledger.store_fact(
            fact=f"KineticEnv initialized: {self.episode_id}",
            metadata={"workspace_id": self.sandbox.workspace_id, "tenant": self.tenant_id}
        )
        
        logger.info(f"KineticEnv Reset: Ready for Episode {self.episode_id}")
        return {"workspace_id": self.sandbox.workspace_id, "step": 0}

    async def step(self, action: str, payload: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Execute an action in the environment with thermodynamic friction and exergy measurement.
        """
        if not self.sandbox:
            raise RuntimeError("Environment must be reset before step.")
            
        self.step_count += 1
        start_time = time.monotonic()
        
        # 1. Maxwell Exergy Check (Filter low-density strings)
        maxwell_res = await self.maxwell.intercept_bus_event(payload)
        exergy_loss = 0
        if not isinstance(maxwell_res, Ok):
            exergy_loss += 10 # Penalty for thermal noise
            return self._build_obs("", "maxwell_rejected", time.monotonic() - start_time, exergy_loss)
            
        # 2. Isolation Execution (Friction)
        # Parse action into command + args roughly
        tokens = action.split(" ")
        command = tokens[0]
        args = tokens[1:]
        
        try:
            res = await self.sandbox.execute(command, args, timeout=timeout)
        except Exception as e:
            res = None
            
        ttft_or_duration = time.monotonic() - start_time
        
        if isinstance(res, Ok):
            out_str = res.value.get("stdout", "")
            err_str = res.value.get("stderr", "")
            exit_code = res.value.get("exit_code", -1)
            status = "success" if exit_code == 0 else "failed"
            output = f"STDOUT:\n{out_str}\nSTDERR:\n{err_str}"
        else:
            output = str(res)
            status = "sandbox_error"
            exergy_loss += 5

        # 3. Ledger Persistence (Causality)
        try:
            await self.ledger.store_fact(
                fact=f"Step {self.step_count} executed: {command}",
                metadata={
                    "episode_id": self.episode_id,
                    "action": action,
                    "duration_s": round(ttft_or_duration, 4),
                    "status": status,
                    "exergy_loss": exergy_loss
                }
            )
        except Exception as e:
            logger.error(f"Failed to persist kinetic step to ledger: {e}")

        return self._build_obs(output, status, ttft_or_duration, exergy_loss)

    def _build_obs(self, output: str, status: str, duration: float, exergy_loss: int) -> Dict[str, Any]:
        return {
            "output": output,
            "status": status,
            "duration": duration,
            "exergy_loss": exergy_loss,
            "step": self.step_count
        }

    async def close(self):
        """Tear down chaos injection and isolation gracefully."""
        await self.chaos.stop()
        if self.sandbox:
            await self.isolation.destroy_workspace(self.sandbox.workspace_id)
            self.sandbox = None
            logger.info(f"KineticEnv Closed: Terminated Episode {self.episode_id}")
