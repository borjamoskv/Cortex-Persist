import threading

# [C5-REAL] Exergy-Maximized
"""OUROBOROS INJECTOR - Synthetic Friction Generator.

Injects stochastic and asymmetric conflicts (friction events) into Redpanda
to stress the Ouroboros Stream Kernel (CQRS Pruning).
"""

import json
import logging
import random
import sys
import time
import uuid

logger = logging.getLogger("cortex.engine.smte.ouroboros_injector")

Producer = None
try:
    from confluent_kafka import Producer  # pyright: ignore[reportMissingImports]
except ImportError:
    logger.warning(
        "confluent_kafka not installed. Synthetic friction injection will fail if invoked."
    )


def delivery_report(err, msg):
    """Callback triggered by Kafka on successful/failed delivery."""
    if err is not None:
        logger.error(f"Delivery failure: {err}")


def inject_synthetic_friction(broker="localhost:9092", num_events=500):
    """Injects an exergy and entropy load into the system.friction bus."""
    if Producer is None:
        logger.error(
            "confluent_kafka is not installed. Cannot inject friction. Run: pip install confluent_kafka"
        )
        sys.exit(1)
    producer = Producer({"bootstrap.servers": broker})

    # Pool of 10 virtual agents
    agent_ids = [f"Agent-Ω-{i}" for i in range(10)]

    logger.info(f"⚡ Starting injection of {num_events} events to {broker}")

    for i in range(num_events):
        agent_id = random.choice(agent_ids)

        # Test determinism: Even agents are limerent (high entropy, low signal)
        # Odd agents are crystalline (high signal, low entropy)
        is_limerent = int(agent_id.split("-")[-1]) % 2 == 0

        if is_limerent:
            signal = random.uniform(0.1, 0.8)
            entropy = random.uniform(3.0, 12.0)  # C > U
        else:
            signal = random.uniform(5.0, 15.0)  # U > C
            entropy = random.uniform(0.1, 1.5)

        event = {
            "event_id": str(uuid.uuid4()),
            "agent_id": agent_id,
            "type": "FRICTION_SEEN",
            "timestamp": int(time.time()),
            "payload": {"signal": signal, "entropy": entropy, "target": None},
        }

        producer.produce(
            "system.friction", value=json.dumps(event).encode("utf-8"), callback=delivery_report
        )
        producer.poll(0)

        # Slight pause to emulate natural streaming
        if i % 50 == 0:
            threading.Event().wait(0.05)  # noqa: TID251

    producer.flush()
    logger.info(
        "✅ Injection completed. The Stream Kernel should have pruned the even agents."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    inject_synthetic_friction()
