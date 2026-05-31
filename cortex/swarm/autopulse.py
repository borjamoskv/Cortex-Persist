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

# AUDITOR-Ω: Entropy spike threshold - override via CORTEX_ENTROPY_THRESHOLD env var
_ENTROPY_THRESHOLD = float(os.environ.get("CORTEX_ENTROPY_THRESHOLD", "0.15"))


async def process_queue():
    """Background loop to consume and execute pending swarm tasks."""
    logger.info("Autopulse Engine: Ignited. Watching swarm queue...")

    try:
        from cortex_rs import AntiLimerenceTopology

        anti_limerence = AntiLimerenceTopology()

        # Inject Ultramap for Endocrinology mapping
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

                    # Update queue file
                    queue["pending_tasks"] = pending
                    with open(SWARM_QUEUE_FILE, "w") as f:
                        json.dump(queue, f, indent=2)

                    # C5-REAL: Execution & OMEGA-X Epistemic Slashing
                    # Initialize massively parallel zero-copy 10k nodes
                    legion = TensorGlialLegion(
                        num_agents=10000, d_dim=10000, file_path="/tmp/tensor_legion.vsa_mmap"
                    )

                    # Apply biological decay (Fading Memory)
                    legion.apply_fading_memory(lambda_decay=0.01)

                    # Log task action inside 1D Centurion 0
                    legion.batch_write_action([0], [f"Process: {payload}"])

                    # Perform Fuzzing/Yield Epistemic Slashing
                    slashed = legion.epistemic_slash_and_respawn(
                        bottom_percentile=10, elite_percentile=90
                    )
                    if slashed > 0:
                        logger.info(
                            "OMEGA-X: Apoptosis activated. %s dead nodes respawned from elite VSA topologies.",
                            slashed,
                        )

                    # AUDITOR-Ω: Entropy spike detection post-process
                    try:
                        _audit_entropy_spike(legion, agent)
                        reality_delta = 0.5  # Positive yield from reality
                    except EntropySpikeException:
                        reality_delta = -1.0  # Harsh rejection from reality (friction)
                        # We don't raise it yet, we let the Rust topological killer decide if it's limerent

                    # ⚡ ANTI-LIMERENCE RUNTIME (C5-REAL)
                    if anti_limerence:
                        # Incubate the agent's specific theory/task
                        try:
                            anti_limerence.incubate_belief(agent)
                            anti_limerence.inject_friction(agent, reality_delta)

                            purged = anti_limerence.execute_kill_switch()
                            if purged:
                                logger.error(
                                    "OUROBOROS KILL-SWITCH: The following agents suffered Epistemic Limerence and were annihilated: %s",
                                    purged,
                                )

                                # 🌊 SHOCKWAVE DE CORTISOL EN ULTRAMAP
                                if umap:
                                    # Deterministically hash agent name to get an approximate coordinate in the swarm topology
                                    agent_hash = int(
                                        hashlib.sha256(agent.encode()).hexdigest()[:16], 16
                                    )
                                    agent_hash % umap.capacity
                                    x = (agent_hash % 1000) / 10.0
                                    y = ((agent_hash >> 4) % 1000) / 10.0
                                    z = ((agent_hash >> 8) % 1000) / 10.0

                                    affected = umap.volume_transmit_hormones(
                                        origin_x=x,
                                        origin_y=y,
                                        origin_z=z,
                                        radius=20.0,
                                        dopamine=0.0,
                                        cortisol=0.9,  # Máximo estrés termodinámico
                                        serotonin=0.0,
                                        adrenaline=0.6,  # Alerta de combate
                                    )
                                    logger.warning(
                                        "🌊 CORTISOL SHOCKWAVE: %s agentes adyacentes estresados por la aniquilación de %s",
                                        affected,
                                        agent,
                                    )

                                if agent in purged:
                                    logger.error("Agent %s was purged! Halting execution.", agent)
                                    continue  # Skip ledger insertion!
                        except Exception as e:
                            logger.error("AntiLimerence Execution Failed: %s", e)

                    if reality_delta < 0:
                        raise EntropySpikeException(f"Entropy Circuit Breaker tripped for {agent}")

                    # Record the 'Success' in the Ledger

                    # Get last hash from state file if possible
                    prev_hash = "GENESIS_BLOCK"
                    if os.path.exists(STATE_FILE):
                        with open(STATE_FILE) as f:
                            state = json.load(f)
                            if state.get("ledgers"):
                                prev_hash = state["ledgers"][-1]["hash"]

                    action = f"SwarmSolve:{agent}"
                    vector_id = payload.get("vector_id", "swarm_task_auto")
                    yield_amount = 1.0  # Unit of Autopoiesis
                    timestamp = time.monotonic()

                    block_payload = f"{prev_hash}_{action}_{vector_id}_{yield_amount}_{timestamp}"
                    block_hash = hashlib.sha256(block_payload.encode()).hexdigest()

                    # Update State File
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

                    # Emit Signal to Pulse (Dashboard)
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
                # Halt further queue processing for 30s to allow metrics to cool down or operators to intervene
                await asyncio.sleep(30.0)
            except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error("Autopulse Queue Error: %s", e)

        await asyncio.sleep(2.0)


class EntropySpikeException(Exception):
    """Raised when swarm yield dispersion exceeds the safety threshold."""

    pass


def _audit_entropy_spike(legion: TensorGlialLegion, agent_name: str) -> None:
    """AUDITOR-Ω Circuit Breaker: Monitor yield entropy spikes per Axiom Ω₃.

    Computes the yield_ratio dispersion across the legion. If the coefficient
    of variation (std/mean) exceeds _ENTROPY_THRESHOLD, emits a P1 alert and
    raises an EntropySpikeException to trip the Circuit Breaker and prevent
    ledger pollution.
    """
    import numpy as np

    yield_ratio = legion.yield_tensor / (legion.token_burn_tensor + 1e-5)
    mean_yield = float(np.mean(yield_ratio))
    std_yield = float(np.std(yield_ratio))

    if mean_yield < 1e-9:
        return  # Cold-start: no data yet

    cv = std_yield / mean_yield  # Coefficient of Variation
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
    else:
        logger.debug(
            "[AUDITOR-Ω] entropy OK - agent=%s cv=%.4f",
            agent_name,
            cv,
        )


if __name__ == "__main__":
    asyncio.run(process_queue())
