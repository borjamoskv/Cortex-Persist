"""
CORTEX v5.2 — Gossip Protocol (KETER-∞ Metal-Level).

Anti-entropy protocol for syncing state between GEACL nodes.
Implements Semantic Digests and Vector Clocks to ensure eventual consistency.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

__all__ = ["GossipProtocol", "StateRecord", "SemanticDigest"]

logger = logging.getLogger("cortex.ha.gossip")


@dataclass(slots=True)
class StateRecord:
    """A record of state conceptually tracked by Gossip."""

    key: str
    value: dict[str, Any]
    version: int
    timestamp: float
    author_node: str

    def compute_hash(self) -> str:
        """Compute semantic digest of the value."""
        # Sort keys to ensure deterministic hashing
        canonical_json = json.dumps(self.value, sort_keys=True)
        return hashlib.sha256(f"{self.key}:{self.version}:{canonical_json}".encode()).hexdigest()


@dataclass(slots=True)
class SemanticDigest:
    """Summary of node state for anti-entropy exchange."""

    node_id: str
    record_hashes: dict[str, str] = field(default_factory=dict)  # key -> hash
    vector_clock: dict[str, int] = field(default_factory=dict)  # node -> version


class GossipProtocol:
    """
    Anti-entropy gossip protocol.
    Syncs Semantic Digests and state records between peers.
    """

    def __init__(
        self,
        node_id: str,
        peers: list[str],
        interval: float = 30.0,
    ):
        self.node_id = node_id
        # We don't couple directly to sqlite conn here anymore;
        # state is purely in-memory for the protocol simulation,
        # or backed by db_writer if integrated later.
        self.peers = set(peers)
        self.interval = interval
        self._running = False
        self._task: asyncio.Task | None = None

        # Local state storage
        self._records: dict[str, StateRecord] = {}
        self._vector_clock: dict[str, int] = {node_id: 0}

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def update_state(self, key: str, value: dict[str, Any]) -> None:
        """Update local state. Increments logical clock."""
        self._vector_clock[self.node_id] = self._vector_clock.get(self.node_id, 0) + 1
        record = StateRecord(
            key=key,
            value=value,
            version=self._vector_clock[self.node_id],
            timestamp=time.time(),
            author_node=self.node_id,
        )
        self._records[key] = record

    def get_state(self, key: str) -> StateRecord | None:
        """Retrieve local state by key."""
        return self._records.get(key)

    def generate_digest(self) -> SemanticDigest:
        """Generate summary digest for anti-entropy exchange."""
        hashes = {k: v.compute_hash() for k, v in self._records.items()}
        return SemanticDigest(
            node_id=self.node_id,
            record_hashes=hashes,
            vector_clock=self._vector_clock.copy(),
        )

    def receive_digest(self, remote_digest: SemanticDigest) -> tuple[list[str], list[StateRecord]]:
        """
        Process remote digest.
        Returns (keys_to_request, records_to_push).
        """
        keys_to_request = []
        records_to_push = []

        local_digest = self.generate_digest()

        # Update local vector clock tracking of remote node
        for node, rv in remote_digest.vector_clock.items():
            lv = self._vector_clock.get(node, 0)
            if rv > lv:
                self._vector_clock[node] = rv

        # Find symmetric difference
        for key, remote_hash in remote_digest.record_hashes.items():
            local_hash = local_digest.record_hashes.get(key)
            if local_hash != remote_hash:
                # We need it, or we have a newer one (conflict resolution happens on fetch)
                # But for simplicity, if hashes differ, we request it.
                keys_to_request.append(key)

        for key, _local_hash in local_digest.record_hashes.items():
            if key not in remote_digest.record_hashes:
                records_to_push.append(self._records[key])

        return keys_to_request, records_to_push

    @staticmethod
    def _record_wins(rr: StateRecord, lr: StateRecord) -> bool:
        """LWW conflict resolution: version → timestamp → author_node (deterministic tie-break)."""
        if rr.version != lr.version:
            return rr.version > lr.version
        if rr.timestamp != lr.timestamp:
            return rr.timestamp > lr.timestamp
        return rr.author_node > lr.author_node

    def receive_records(self, remote_records: list[StateRecord]) -> None:
        """Process incoming full state records. Last-Write-Wins fallback."""
        for rr in remote_records:
            lr = self._records.get(rr.key)
            if lr is None or self._record_wins(rr, lr):
                self._records[rr.key] = rr
                self._vector_clock[rr.author_node] = max(
                    self._vector_clock.get(rr.author_node, 0), rr.version
                )

    def start(self) -> None:
        """Start gossip loop (schedules background task in the running event loop)."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._gossip_loop())
        logger.info("GossipProtocol started on node %s", self.node_id)

    async def stop(self) -> None:
        """Stop gossip loop."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.debug("GossipProtocol task cancelled cleanly on %s", self.node_id)
                raise
        logger.info("GossipProtocol stopped on node %s", self.node_id)

    async def _gossip_loop(self) -> None:
        """Background loop to pick a peer and sync."""
        while self._running:
            try:
                if self.peers:
                    peer = random.choice(list(self.peers))
                    await self._perform_gossip(peer)
            except (OSError, RuntimeError) as e:
                logger.error("Gossip error on %s: %s", self.node_id, e)

            await asyncio.sleep(self.interval)

    async def _perform_gossip(self, peer: str) -> None:
        """
        Perform gossip exchange with a peer in the network.
        (Usually overridden by a subclass or injected network layer).
        """
        pass
