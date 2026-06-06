import asyncio
import hashlib
import json
import logging
import os
import time
from cortex.config import DB_PATH
from cortex.extensions.signals.bus import AsyncSignalBus
from cortex.swarm.tensor_glial import TensorGlialLegion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.swarm.autopulse")
SWARM_QUEUE_FILE = "/tmp/cortex_swarm_queue.json"
STATE_FILE = "/tmp/cortex_state.json"
_ENTROPY_THRESHOLD = float(os.environ.get("CORTEX_ENTROPY_THRESHOLD", "0.15"))


async def process_queue() -> None:
    """Background loop to consume and execute pending swarm tasks."""
    logger.info("Autopulse Engine: Ignited. Watching swarm queue...")
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
    except ImportError as e:
        anti_limerence = None
        umap = None
        logger.warning("C5-REAL: Anti-Limerence/Ultramap Runtime NOT found: %s", e)
    while True:
        if os.path.exists(SWARM_QUEUE_FILE):
            try:
                with open(SWARM_QUEUE_FILE) as f:
                    queue = json.load(f)
                pending = queue.get("pending_tasks", [])
                if pending:
                    task = pending.pop(0)
                    agent = task.get("agent", "Unknown")
                    payload = task.get("payload", {})
                    logger.info("Autopoiesis: Processing task for %s...", agent)
                    queue["pending_tasks"] = pending
                    with open(SWARM_QUEUE_FILE, "w") as f:
                        json.dump(queue, f, indent=2)
                    legion = TensorGlialLegion(
                        num_agents=10000, d_dim=10000, file_path="/tmp/tensor_legion.vsa_mmap"
                    )
                    legion.apply_fading_memory(lambda_decay=0.01)
                    legion.batch_write_action([0], [f"Process: {payload}"])
                    slashed = legion.epistemic_slash_and_respawn(
                        bottom_percentile=10, elite_percentile=90
                    )
                    if slashed > 0:
                        logger.info(
                            "OMEGA-X: Apoptosis activated. %s dead nodes respawned from elite VSA topologies.",
                            slashed,
                        )
                    try:
                        _audit_entropy_spike(legion, agent)
                        reality_delta = 0.5
                    except EntropySpikeException:
                        reality_delta = -1.0
                    if anti_limerence:
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
                                    agent_hash = int(
                                        hashlib.sha256(agent.encode()).hexdigest()[:16], 16
                                    )
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
                                if agent in purged:
                                    logger.error("Agent %s was purged! Halting execution.", agent)
                                    continue
                        except Exception as e:
                            logger.error("AntiLimerence Execution Failed: %s", e)
                    if reality_delta < 0:
                        raise EntropySpikeException(f"Entropy Circuit Breaker tripped for {agent}")
                    prev_hash = "GENESIS_BLOCK"
                    if os.path.exists(STATE_FILE):
                        with open(STATE_FILE) as f:
                            state = json.load(f)
                            if state.get("ledgers"):
                                prev_hash = state["ledgers"][-1]["hash"]
                    action = f"SwarmSolve:{agent}"
                    vector_id = payload.get("vector_id", "swarm_task_auto")
                    yield_amount = 1.0
                    timestamp = time.monotonic()
                    block_payload = f"{prev_hash}_{action}_{vector_id}_{yield_amount}_{timestamp}"
                    block_hash = hashlib.sha256(block_payload.encode()).hexdigest()
                    if not os.path.exists(STATE_FILE):
                        state = {"ledgers": []}
                    else:
                        with open(STATE_FILE) as f:
                            state = json.load(f)
                    state["ledgers"].append(
                        {
                            "timestamp": timestamp,
                            "action": action,
                            "vector_id": vector_id,
                            "yield_amount": yield_amount,
                            "hash": block_hash,
                        }
                    )
                    with open(STATE_FILE, "w") as f:
                        json.dump(state, f, indent=2)
                    try:
                        import aiosqlite

                        async with aiosqlite.connect(DB_PATH) as conn:
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
            except EntropySpikeException as e:
                logger.error(
                    "Autopulse Circuit Breaker Tripped! Task aborted for %s. Error: %s", agent, e
                )
                await asyncio.sleep(30.0)
            except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error("Autopulse Queue Error: %s", e)
        await asyncio.sleep(2.0)


class EntropySpikeException(Exception):
    """Raised when swarm yield dispersion exceeds the safety threshold."""


def _audit_entropy_spike(legion: TensorGlialLegion, agent_name: str) -> None:
    """AUDITOR-Ω Circuit Breaker: Monitor yield entropy spikes per Axiom Ω₃.

    Computes the yield_ratio dispersion across the legion. If the coefficient
    of variation (std/mean) exceeds _ENTROPY_THRESHOLD, emits a P1 alert and
    raises an EntropySpikeException to trip the Circuit Breaker and prevent
    ledger pollution.
    """
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
    asyncio.run(process_queue())
