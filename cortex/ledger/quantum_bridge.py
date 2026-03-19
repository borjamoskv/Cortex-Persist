"""
cortex/ledger/quantum_bridge.py — UQPL-H Implementation Foundation.
Axioma Ω₁₆: Symbolic Quantum Mapping for Agent Ledgers.

Este módulo permite tratar el DAG (Directed Acyclic Graph) de hechos de CORTEX
como un estado de sistema cuántico, donde la verificación actúa como medida.
Añade soporte P2P asíncrono vía EntanglementBus para sincronía de enjambres.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("cortex.ledger.quantum")


class QuantumState(Enum):
    """Estados del ciclo de vida de un hecho bajo el paradigma UQPL."""

    SUPERPOSITION = "psi"  # Hecho conjeturado, no verificado por Guard (Ω₁)
    COLLAPSED = "bit"  # Hecho medido y persistido en el Ledger determinista
    ENTANGLED = "bell"  # Hecho con dependencias causales activas


@dataclass
class EntangledNode:
    """Representación simbólica de un hecho como Qubit de información."""

    fact_id: str
    state: QuantumState = QuantumState.SUPERPOSITION
    fidelity: float = 1.0  # 1.0 - Entropy Residue (Ω₂)
    entangled_with: list[str] = field(default_factory=list)  # Causal Edges
    hash_signature: str | None = None
    collapsed_at: float | None = None


class EntanglementBus:
    """Zero-Dependency Virtual Bus para propagar colapsos entre QuantumBridges.
    Simula una red Redis Pub/Sub o red Kademlia en memoria.
    """

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def broadcast(self, sender_id: str, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "sender_id": sender_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        }
        for q in self._subscribers:
            await q.put(event)


# Global singleton bus para la red virtual en el proceso (P2P simulado)
GLOBAL_ENTANGLEMENT_BUS = EntanglementBus()


class QuantumLedgerBridge:
    """Puente arquitectónico entre SQLite Clásico y Lógica UQPL con Sincronía Federada."""

    def __init__(self, node_id: str, store: Any = None, bus: EntanglementBus | None = None) -> None:
        self.node_id = node_id
        self._store = store
        self._registry: dict[str, EntangledNode] = {}
        self._bus = bus or GLOBAL_ENTANGLEMENT_BUS
        self._listen_queue = self._bus.subscribe()
        self._listener_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
        self._bus.unsubscribe(self._listen_queue)

    async def _listen(self) -> None:
        """Escucha eventos de colapso en la red cuántica para sincronizar el DAG local."""
        try:
            while True:
                event = await self._listen_queue.get()
                if event["sender_id"] != self.node_id:
                    await self._process_network_event(event)
                self._listen_queue.task_done()
        except asyncio.CancelledError:
            pass

    async def _process_network_event(self, event: dict[str, Any]) -> None:
        """Responde a un evento de la red."""
        event_type = event["event_type"]
        payload = event["payload"]

        if event_type == "COLLAPSE":
            fact_id = payload["fact_id"]
            signature = payload["signature"]
            if (
                fact_id in self._registry
                and self._registry[fact_id].state != QuantumState.COLLAPSED
            ):
                node = self._registry[fact_id]
                node.state = QuantumState.COLLAPSED
                node.hash_signature = signature
                node.collapsed_at = payload["timestamp"]
                logger.info(
                    "⚡ [SYNCHRONY] Node %s received remote collapse for Fact %s",
                    self.node_id,
                    fact_id,
                )

                # Propagar colapso a estados entrelazados locales
                for entangled_id in node.entangled_with:
                    if (
                        entangled_id in self._registry
                        and self._registry[entangled_id].state != QuantumState.COLLAPSED
                    ):
                        logger.warning(
                            "💥 [CASCADE] Fact %s collapsed due to Entanglement with %s",
                            entangled_id,
                            fact_id,
                        )
                        await self.apply_observation(entangled_id)

    def register_fact(self, fact_id: str, state: QuantumState = QuantumState.SUPERPOSITION) -> None:
        """Registra la entrada de un hecho en el espacio de Hilbert del Ledger."""
        self._registry[fact_id] = EntangledNode(fact_id=fact_id, state=state)
        logger.debug(
            "🌐 [UQPL] Node %s: Fact %s registered in state %s", self.node_id, fact_id, state
        )

    async def apply_observation(self, fact_id: str) -> bool:
        """Colapsa la función de onda de un hecho depositado en el Ledger, emitiendo Sincronía."""
        if fact_id not in self._registry:
            return False

        node = self._registry[fact_id]
        if node.state != QuantumState.COLLAPSED:
            node.state = QuantumState.COLLAPSED
            node.collapsed_at = time.time()
            node.hash_signature = hashlib.sha256(
                f"{fact_id}:{node.collapsed_at}".encode()
            ).hexdigest()
            logger.info("⚡ [COLLAPSE] Node %s: Fact %s measured and fixed.", self.node_id, fact_id)

            # Broadcast the collapse to the federation
            await self._bus.broadcast(
                self.node_id,
                "COLLAPSE",
                {
                    "fact_id": fact_id,
                    "signature": node.hash_signature,
                    "timestamp": node.collapsed_at,
                },
            )
            return True

        return False

    def entangle(self, source_id: str, target_id: str) -> None:
        """Crea un entrelazamiento causal (Bell state) entre dos hechos."""
        if source_id in self._registry and target_id in self._registry:
            self._registry[source_id].entangled_with.append(target_id)
            self._registry[source_id].state = QuantumState.ENTANGLED
            self._registry[target_id].state = QuantumState.ENTANGLED
            logger.debug(
                "🔗 [ENTANGLE] Bell state created on %s: %s <-> %s",
                self.node_id,
                source_id,
                target_id,
            )
