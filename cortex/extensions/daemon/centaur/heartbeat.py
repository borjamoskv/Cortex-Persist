"""
CORTEX V5 - Continuous Autopoiesis (Heartbeat Daemon).
Vector 1 of the Singularity: non-discrete temporal execution.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from cortex.engine.auth import ByzantineAuthLayer
from cortex.engine.decalcifier import SovereignDecalcifier
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.extensions.daemon.actuators import PhysicalActuator
from cortex.extensions.daemon.centaur.queue import EntropicQueue
from cortex.extensions.swarm.centauro_engine import CentauroEngine, Formation
from cortex.extensions.ui.pulmones import SystemRespiration

logger = logging.getLogger("moskv-daemon.centaur.heartbeat")

ITURRIA_DIR = Path.home() / ".cortex" / "iturria"


class HeartbeatDaemon:
    """
    The background engine that continuously evaluates the Entropic Queue
    and delegates task to the Centauro Swarm.
    """

    def __init__(
        self,
        queue: EntropicQueue,
        engine: CentauroEngine,
        poll_interval: float = 60.0,
    ):
        self.queue = queue
        self.engine = engine
        self._poll_interval = poll_interval
        self._shutdown_event = asyncio.Event()

        ITURRIA_DIR.mkdir(parents=True, exist_ok=True)

    async def _decalcifier_loop(self) -> None:
        """Pure async task that wakes 1x/hour, evaluates Cortisol, and decalcifies 500 facts."""
        logger.info("🧬 decalcifier_loop started (Hourly Cortisol evaluations).")
        decalcifier = SovereignDecalcifier()

        while not self._shutdown_event.is_set():
            await asyncio.sleep(3600.0)  # Wait 1 hour

            if self._shutdown_event.is_set():
                break

            try:
                # Evaluer Cortisol (Sistema relajado)
                cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)
                if cortisol > 0.4:
                    logger.debug(
                        "🧬 [Ω₃-E+] Decalcifier skipped: Cortisol too high (%.2f).", cortisol
                    )
                    continue

                logger.info(
                    "🧬 [Ω₃-E+] Cortisol low (%.2f). Starting decalcification (REM phase).",
                    cortisol,
                )

                from cortex.extensions.daemon.models import CORTEX_DB

                async with aiosqlite.connect(CORTEX_DB, timeout=5.0) as conn:
                    await decalcifier.decalcify_cycle(conn)

            except Exception as e:  # noqa: BLE001
                logger.error("🧬 [Ω₃-E+] Decalcifier hourly loop error: %s", e)

    async def start(self) -> None:
        """Start the continuous autopoiesis loop."""
        logger.info("❤️  HeartbeatDaemon (Continuous Autopoiesis) loop started.")
        self._shutdown_event.clear()

        self._decalcifier_task = asyncio.create_task(self._decalcifier_loop())

        while not self._shutdown_event.is_set():
            try:
                # 1. System Respiration check: How intensely should we act?
                throttle_multiplier, swarm_size_limit, ok_to_run = (
                    SystemRespiration.get_current_state()
                )

                if not ok_to_run:
                    logger.debug("HeartbeatDaemon sleeping (System Respiration threshold).")
                    await asyncio.sleep(self._poll_interval * 2)
                    continue

                # 2. Pop next task
                task = self.queue.pop()
                if not task:
                    # No tasks, enter shallow breath
                    await asyncio.sleep(self._poll_interval * throttle_multiplier)
                    continue

                logger.info("Heartbeat processing task: %s (%s)", task["id"], task["type"])

                # 3. Determine if it's a Physical Parity task
                if task["type"] in ["PHYSICAL", "OS_COMMAND"]:
                    await self._handle_physical_task(task)
                    await asyncio.sleep(self._poll_interval * throttle_multiplier)
                    continue

                # 4. Determine Formation based on task and respiration limits
                formation = self._determine_formation(task["type"], swarm_size_limit)

                # 5. Engage Centauro Swarm
                prompt = self._build_prompt(task)
                result = await self.engine.engage(mission=prompt, formation=formation)

                # 6. Handle Result
                if result.get("status") in ["success", "aleph_breakthrough"]:
                    self._deposit_to_iturria(task, result)  # type: ignore[type-error]
                    self.queue.mark_completed(task["id"])
                    logger.info("Task %s completed successfully via %s.", task["id"], formation)
                else:
                    reason = result.get("reason", "Consensus Failed")
                    self.queue.mark_failed(task["id"], reason)
                    logger.warning("Task %s failed: %s", task["id"], reason)

                # Cool down after heavy processing
                await asyncio.sleep(self._poll_interval * throttle_multiplier)

            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("Heartbeat loop error: %s", e)
                await asyncio.sleep(10.0)

    async def stop(self) -> None:
        """Gracefully stop the daemon."""
        logger.info("Stopping HeartbeatDaemon...")
        self._shutdown_event.set()

    async def _handle_physical_task(self, task: dict) -> None:
        """Execute tasks that require direct OS interaction (Vector 4)."""
        logger.warning("⚡ [PHYSICAL PARITY] Executing root task: %s", task["id"])
        payload = task.get("payload", {})
        command = payload.get("command")

        if not command:
            self.queue.mark_failed(task["id"], "No physical command provided")
            return

        # AX-003: Byzantine Auth (Verify, then Trust)
        is_authorized = await ByzantineAuthLayer.acquire_lock(
            intent="OS_COMMAND", payload=payload, zenith_score=float(payload.get("zenith", 0.0))
        )

        if not is_authorized:
            logger.error("⚡ [PHYSICAL PARITY] Task rejected by Byzantine Consensus (Auth Failed)")
            self.queue.mark_failed(
                task["id"], "Byzantine Auth verification timed out or was explicitly rejected."
            )
            return

        result = await PhysicalActuator.ekin_execute_shell(command)

        if result["status"] == "success":
            stdout = result.get("stdout", "")
            self._deposit_to_iturria(
                task,
                {
                    "formation": "EKIN-BINDING",
                    "agents_used": 1,
                    "solution": (
                        f"Command Executed Successfully." f"\n\nSTDOUT:\n```\n{stdout}\n```"
                    ),
                },
            )
            self.queue.mark_completed(task["id"])
            logger.warning("⚡ [PHYSICAL PARITY] Completed successfully.")
        else:
            self.queue.mark_failed(task["id"], result.get("stderr", "Unknown Execution Error"))
            logger.error("⚡ [PHYSICAL PARITY] Failed: %s", result.get("stderr"))

    def _determine_formation(self, task_type: str, max_size: int) -> str:
        """Select Swarm Formation based on task type and current system capacity."""
        if task_type == "REFACTOR":
            target = Formation.OUROBOROS
        elif task_type == "RESEARCH":
            target = Formation.SIEGE
        elif task_type == "OSINT":
            target = Formation.SPECTRE
        elif task_type == "AUDIT":
            target = Formation.PHALANX
        else:
            target = Formation.BLITZ

        # Ensure we don't spawn a LEVIATHAN if the system wants to sleep
        target_size = CentauroEngine._FORMATION_SIZES.get(target, 3)
        if target_size > max_size:
            logger.debug("Downgrading formation from %s due to system load.", target)
            return Formation.BLITZ if max_size < 5 else Formation.PHALANX

        return target

    def _build_prompt(self, task: dict) -> str:
        """Construct the prompt for the swarm."""
        payload = task["payload"]
        if task["type"] == "RESEARCH":
            return f"Deep dive on: {payload.get('topic')}. Context: {payload.get('context', '')}"
        elif task["type"] == "REFACTOR":
            return f"Apply BERRERAIKI pattern to file: {payload.get('file_path')}"
        return f"Task type {task['type']}: {json.dumps(payload)}"

    def _deposit_to_iturria(self, task: dict, result: dict) -> None:
        """Save the swarm consensus to the Dream Layer for operator review."""
        now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_id = task["id"][:8]
        filename = f"{task['type']}_{now}_{safe_id}.md"

        content = f"# Autonomous Swarm Result: {task['type']}\n\n"
        content += f"**Task ID:** {task['id']}\n"
        content += f"**Formation:** {result.get('formation')}\n"
        content += f"**Agents Used:** {result.get('agents_used')}\n\n"
        content += "## Consensus Payload\n"
        content += f"{result.get('solution')}\n\n"

        filepath = ITURRIA_DIR / filename
        filepath.write_text(content, encoding="utf-8")
        logger.info("Deposited result to Dream Layer: %s", filepath)
