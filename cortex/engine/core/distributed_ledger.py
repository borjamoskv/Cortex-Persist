# [C5-REAL] Exergy-Maximized
"""
Vector C: Distributed Ledger Bridge (Redpanda).
Extends the EvolutionLedger to broadcast and consume mutations across an L6 Swarm.
"""

import json
import logging
from collections.abc import Iterator
from typing import Any

try:
    from confluent_kafka import Consumer, Producer

    KAFKA_AVAILABLE = True
except ImportError:
    Consumer = Any
    Producer = Any
    KAFKA_AVAILABLE = False

from cortex.engine.core.evolution_ledger import (
    ControlVector,
    EvolutionLedger,
    MutationRecord,
    _canonical_json,
)

logger = logging.getLogger("cortex.distributed_ledger")


class DistributedEvolutionLedger(EvolutionLedger):
    """
    Extends the local EvolutionLedger with Kafka/Redpanda broadcasting.
    Local mutations are written to the JSONL log as normal, but ALSO
    produced to a Kafka topic for multi-node consensus.
    """

    def __init__(
        self,
        log_path: str | None = None,
        kafka_brokers: str = "localhost:9092",
        topic: str = "cortex-evolution-ledger",
    ):
        super().__init__(log_path=log_path)
        self.topic = topic
        self.kafka_brokers = kafka_brokers
        self._producer = Producer(
            {
                "bootstrap.servers": self.kafka_brokers,
                "client.id": "cortex-node-producer",
                "acks": "all",
                "linger.ms": 5,
            }
        )
        logger.info(
            f"DistributedEvolutionLedger connected to {self.kafka_brokers} [topic: {self.topic}]"
        )

    def _delivery_report(self, err: Any, msg: Any) -> None:
        if err is not None:
            logger.error(f"Redpanda delivery failed: {err}")
        else:
            logger.debug(
                f"Redpanda delivered: {msg.topic()} [{msg.partition()}] at offset {msg.offset()}"
            )

    def record_mutation(
        self,
        agent_idx: int,
        vector_after: ControlVector,
        vector_before: ControlVector | None = None,
        performance_delta: float | None = None,
        source: str = "substrate",
        metadata: dict[str, Any] | None = None,
    ) -> MutationRecord:
        """Records mutation locally AND broadcasts to Redpanda."""

        # 1. Local append and hash chaining (O(1) latency block)
        record = super().record_mutation(
            agent_idx=agent_idx,
            vector_after=vector_after,
            vector_before=vector_before,
            performance_delta=performance_delta,
            source=source,
            metadata=metadata,
        )

        # 2. Async broadcast to Redpanda
        payload_line = _canonical_json(record.to_payload())
        try:
            self._producer.produce(
                self.topic,
                key=str(agent_idx).encode("utf-8"),
                value=payload_line.encode("utf-8"),
                callback=self._delivery_report,
            )
            self._producer.poll(0)
        except Exception as e:
            logger.error(f"Failed to produce mutation to Redpanda: {e}")

        return record

    def flush(self, timeout: float = 5.0) -> None:
        """Ensure all messages are delivered before shutdown."""
        self._producer.flush(timeout)


class LedgerConsumer:
    """Consumes the distributed ledger and reconstructs state on replica nodes."""

    def __init__(
        self,
        kafka_brokers: str = "localhost:9092",
        topic: str = "cortex-evolution-ledger",
        group_id: str = "cortex-replica-group",
    ):
        self.topic = topic
        self._consumer = Consumer(
            {
                "bootstrap.servers": kafka_brokers,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
            }
        )
        self._consumer.subscribe([self.topic])
        logger.info(f"LedgerConsumer subscribed to {topic} at {kafka_brokers}")

    def consume_stream(self, timeout: float = 1.0) -> Iterator[MutationRecord]:
        """Yields MutationRecords as they arrive over the network."""
        while True:
            msg = self._consumer.poll(timeout)
            if msg is None:
                continue
            if msg.error():
                logger.error(f"Consumer error: {msg.error()}")
                continue

            try:
                payload = json.loads(msg.value().decode("utf-8"))
                record = MutationRecord.from_payload(payload)
                yield record
            except Exception as e:
                logger.error(f"Corrupt message received over network: {e}")

    def close(self):
        self._consumer.close()
