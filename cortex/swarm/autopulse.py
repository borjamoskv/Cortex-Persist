# [C5-REAL] Exergy-Maximized
import asyncio
import json
import logging
import os
import time

from cortex.config import DB_PATH
from cortex.crypto.provider import HashProvider
from cortex.database.core import connect_async_ctx
from cortex.swarm.tensor_glial import TensorGlialLegion
from cortex_extensions.signals.bus import AsyncSignalBus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.swarm.autopulse")
SWARM_QUEUE_FILE = "/tmp/cortex_swarm_queue.json"
STATE_FILE = "/tmp/cortex_state.json"
_ENTROPY_THRESHOLD = float(os.environ.get("CORTEX_ENTROPY_THRESHOLD", "0.15"))


class TensorProvider:
    """Lazy Singleton Provider for the TensorGlialLegion mmap."""

    _tensor: TensorGlialLegion | None = None
    _lock = asyncio.Lock()

    @classmethod
    async def get(cls) -> TensorGlialLegion:
        if cls._tensor is None:
            async with cls._lock:
                if cls._tensor is None:
                    cls._tensor = await asyncio.to_thread(cls._init_tensor)
        return cls._tensor

    @staticmethod
    def _init_tensor() -> TensorGlialLegion:
        """CPU/Disk intensive initialization."""
        legion = TensorGlialLegion(
            num_agents=10000, d_dim=10000, file_path="/tmp/tensor_legion.vsa_mmap"
        )
        legion.apply_fading_memory(lambda_decay=0.01)
        return legion


def _load_anti_limerence_runtime() -> tuple:
    """Loads anti-limerence and ultramap modules if available."""
    try:
        from cortex_rs import AntiLimerenceTopology

        anti_limerence = AntiLimerenceTopology()
        import sys

        sys.path.append(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "cortex-core"))
        )
        from ultramap import UltramapSubstrate

        umap = UltramapSubstrate(capacity=10000)
        logger.info("C5-REAL: Anti-Limerence Runtime & Ultramap Endocrinology Engaged")
        return anti_limerence, umap
    except ImportError as e:
        logger.warning("C5-REAL: Anti-Limerence/Ultramap Runtime NOT found: %s", e)
        return None, None


def _consume_next_task_sync() -> tuple[str, dict] | None:
    """Synchronous file I/O and JSON parsing for reading next task. Must be wrapped in to_thread."""
    if not os.path.exists(SWARM_QUEUE_FILE):
        return None
    try:
        with open(SWARM_QUEUE_FILE) as f:
            queue = json.load(f)
        pending = queue.get("pending_tasks", [])
        if not pending:
            return None
        task = pending.pop(0)
        agent = task.get("agent", "Unknown")
        payload = task.get("payload", {})
        queue["pending_tasks"] = pending
        with open(SWARM_QUEUE_FILE, "w") as f:
            json.dump(queue, f, indent=2)
        return agent, payload
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error("Autopulse Queue Error: %s", e)
        return None


async def _consume_next_task() -> tuple[str, dict] | None:
    """Reads and parses the next pending task asynchronously without blocking the event loop."""
    return await asyncio.to_thread(_consume_next_task_sync)


def _trigger_umap_hormones(agent: str, umap) -> None:
    """Triggers hormonal stress response in adjacent agents."""
    agent_hash = int(HashProvider.sha256(agent)[:16], 16)
    agent_hash % umap.capacity
    x = agent_hash % 1000 / 10.0
    y = (agent_hash >> 4) % 1000 / 10.0
    z = (agent_hash >> 8) % 1000 / 10.0
    affected = umap.volume_transmit_hormones(
        origin_x=x,
        origin_y=y,
        origin_z=z,
        radius=20.0,
        dopamine=0.0,
        cortisol=0.9,
        serotonin=0.0,
        adrenaline=0.6,
    )
    logger.warning(
        "🌊 CORTISOL SHOCKWAVE: %s agentes adyacentes estresados por la aniquilación de %s",
        affected,
        agent,
    )


def _execute_anti_limerence_sync(agent: str, reality_delta: float, anti_limerence, umap) -> bool:
    """Synchronous logic for incubating belief and processing kill switch."""
    if not anti_limerence:
        return False
    try:
        anti_limerence.incubate_belief(agent)
        anti_limerence.inject_friction(agent, reality_delta)
        purged = anti_limerence.execute_kill_switch()
        if purged:
            logger.error(
                "OUROBOROS KILL-SWITCH: The following agents suffered Epistemic Limerence and were annihilated: %s",
                purged,
            )
            if umap:
                _trigger_umap_hormones(agent, umap)
            if agent in purged:
                logger.error("Agent %s was purged! Halting execution.", agent)
                return True
    except Exception as e:
        logger.error("AntiLimerence Execution Failed: %s", e)
    return False


def _write_ledger_sync(agent: str, payload: dict) -> str:
    """Synchronous file I/O for appending to the state ledger. Returns block_hash."""
    prev_hash = "GENESIS_BLOCK"
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
                if state.get("ledgers"):
                    prev_hash = state["ledgers"][-1]["hash"]
        except Exception as exc:
            logger.warning("Suppressed exception: %s", exc)

    action = f"SwarmSolve:{agent}"
    vector_id = payload.get("vector_id", "swarm_task_auto")
    yield_amount = 1.0
    timestamp = time.monotonic()

    block_payload = f"{prev_hash}_{action}_{vector_id}_{yield_amount}_{timestamp}"
    block_hash = HashProvider.sha256(block_payload)

    if not os.path.exists(STATE_FILE):
        state = {"ledgers": []}
    else:
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            state = {"ledgers": []}

    state["ledgers"].append(
        {
            "timestamp": timestamp,
            "action": action,
            "vector_id": vector_id,
            "yield_amount": yield_amount,
            "hash": block_hash,
        }
    )
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except OSError as e:
        logger.error("Error writing state file: %s", e)

    return block_hash


async def _append_state_ledger(agent: str, payload: dict) -> None:
    """Appends task resolution asynchronously to state file and emits signal."""
    block_hash = await asyncio.to_thread(_write_ledger_sync, agent, payload)

    action = f"SwarmSolve:{agent}"
    vector_id = payload.get("vector_id", "swarm_task_auto")
    yield_amount = 1.0

    try:
        import aiosqlite

        async with connect_async_ctx(DB_PATH) as conn:
            bus = AsyncSignalBus(conn)
            await bus.emit(
                "ledger_append",
                payload={
                    "hash": block_hash,
                    "action": action,
                    "vector_id": vector_id,
                    "yield_amount": yield_amount,
                },
            )
            logger.info("Autopulse: Ledger signal emitted for %s", block_hash[:8])
    except (OSError, aiosqlite.Error, RuntimeError) as e:
        logger.error("Autopulse Signal Error: %s", e)


def _process_tensor_sync(legion: TensorGlialLegion, agent: str, payload: dict) -> float:
    """CPU-heavy synchronous tensor operations. Returns reality_delta."""
    legion.batch_write_action([0], [f"Process: {payload}"])
    slashed = legion.epistemic_slash_and_respawn(bottom_percentile=10, elite_percentile=90)
    if slashed > 0:
        logger.info(
            "OMEGA-X: Apoptosis activated. %s dead nodes respawned from elite VSA topologies.",
            slashed,
        )

    try:
        _audit_entropy_spike(legion, agent)
        return 0.5
    except EntropySpikeException:
        return -1.0


async def _process_single_task(agent: str, payload: dict, anti_limerence, umap) -> None:
    """Executes a single task from the queue, including VSA operations and validation."""
    logger.info("Autopoiesis: Processing task for %s...", agent)

    # 1. Lazy Tensor Singleton Init
    t0 = time.monotonic()
    legion = await TensorProvider.get()
    t_init = (time.monotonic() - t0) * 1000.0

    if t_init > 5.0:
        logger.info("Telemetry | Tensor Init Time: %.2f ms", t_init)
    else:
        logger.debug("Telemetry | Tensor Warm Time: %.2f ms", t_init)

    # 2. Process Tensor heavily in separate thread
    reality_delta = await asyncio.to_thread(_process_tensor_sync, legion, agent, payload)

    # 3. Process Limerence
    purged = await asyncio.to_thread(
        _execute_anti_limerence_sync, agent, reality_delta, anti_limerence, umap
    )
    if purged:
        return

    if reality_delta < 0:
        raise EntropySpikeException(f"Entropy Circuit Breaker tripped for {agent}")

    await _append_state_ledger(agent, payload)


async def process_queue() -> None:
    """Background loop to consume and execute pending swarm tasks."""
    logger.info("Autopulse Engine: Ignited. Watching swarm queue...")
    anti_limerence, umap = _load_anti_limerence_runtime()

    last_pulse = time.monotonic()

    try:
        while True:
            current_time = time.monotonic()
            loop_lag = (current_time - last_pulse) * 1000.0

            # 2s is the sleep interval, overhead shouldn't push it beyond 3s typically
            if loop_lag > 3000.0:
                logger.warning("Telemetry | High Loop Lag detected: %.1f ms", loop_lag)

            task_data = await _consume_next_task()
            if task_data:
                agent, payload = task_data
                try:
                    await _process_single_task(agent, payload, anti_limerence, umap)
                except EntropySpikeException as e:
                    logger.error(
                        "Autopulse Circuit Breaker Tripped! Task aborted for %s. Error: %s",
                        agent,
                        e,
                    )
                    await asyncio.sleep(30.0)
                except Exception as e:
                    logger.error("Unexpected error processing task: %s", e)

            await asyncio.sleep(2.0)
            last_pulse = time.monotonic()

    except asyncio.CancelledError:
        logger.info("Autopulse Engine: Cancelled signal received. Shutting down cleanly.")
        raise


class EntropySpikeException(Exception):
    """Raised when swarm yield dispersion exceeds the safety threshold."""


def _audit_entropy_spike(legion: TensorGlialLegion, agent_name: str) -> None:
    """AUDITOR-Ω Circuit Breaker: Monitor yield entropy spikes per Axiom Ω₃."""
    import numpy as np

    yield_ratio = legion.yield_tensor / (legion.token_burn_tensor + 1e-05)
    mean_yield = float(np.mean(yield_ratio))
    std_yield = float(np.std(yield_ratio))
    if mean_yield < 1e-09:
        return
    cv = std_yield / mean_yield
    if cv > _ENTROPY_THRESHOLD:
        logger.error(
            "[AUDITOR-Ω] CIRCUIT BREAKER TRIPPED! Entropy Spike Detected - agent=%s cv=%.4f threshold=%.4f sha256=%s",
            agent_name,
            cv,
            _ENTROPY_THRESHOLD,
            legion.global_sha256_audit()[:16],
        )
        raise EntropySpikeException(
            f"Entropy Circuit Breaker tripped for agent {agent_name} (cv={cv:.4f})"
        )
    logger.debug("[AUDITOR-Ω] entropy OK - agent=%s cv=%.4f", agent_name, cv)


if __name__ == "__main__":
    try:
        asyncio.run(process_queue())
    except KeyboardInterrupt:
        logger.info("Autopulse terminated by user.")
