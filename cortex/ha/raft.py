"""
CORTEX v5.0 — Raft Consensus Implementation.

Handles leader election and log replication state.
"""

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from enum import Enum

import aiosqlite

__all__ = ["NodeRole", "RaftNode"]

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"


class RaftNode:
    """
    Raft Consensus Node.

    Manages node state, election timeouts, and role transitions.
    Does not fully implement the log replication state machine (yet),
    focuses on Leader Election for the HA cluster.
    """

    HEARTBEAT_INTERVAL = 1.0  # seconds
    ELECTION_TIMEOUT_MIN = 3.0
    ELECTION_TIMEOUT_MAX = 6.0

    def __init__(
        self,
        node_id: str,
        conn: aiosqlite.Connection,
        peers: list[str],
        state_callback: Callable[[NodeRole], Awaitable[None]] | None = None,
    ):
        self.node_id = node_id
        self.conn = conn
        self.peers = peers
        self.state_callback = state_callback

        self.role = NodeRole.FOLLOWER
        self.current_term = 0
        self.voted_for: str | None = None
        self.leader_id: str | None = None

        self.last_heartbeat = time.monotonic()
        self._running = False
        self._election_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._heartbeat_event = asyncio.Event()  # signals arrival of heartbeat

    async def start(self) -> None:
        """Start the Raft node lifecycle."""
        self._running = True
        self._election_task = asyncio.create_task(self._election_loop())
        logger.info("RaftNode %s started as FOLLOWER", self.node_id)

    async def stop(self) -> None:
        """Stop the Raft node gracefully, awaiting task termination."""
        self._running = False
        self._heartbeat_event.set()  # unblock election_loop if sleeping
        for task in (self._election_task, self._heartbeat_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._election_task = None
        self._heartbeat_task = None
        logger.info("RaftNode %s stopped", self.node_id)

    async def _election_loop(self):
        """Monitor heartbeat and trigger elections using event-driven sleep.

        Instead of polling every 0.1s, we sleep exactly until the randomised
        election timeout expires.  A heartbeat arrival wakes us early via
        _heartbeat_event, resetting the wait so we never start a spurious
        election while the leader is healthy.
        """
        while self._running:
            if self.role == NodeRole.LEADER:
                # Leaders don't need election timeouts; yield and re-check.
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                continue

            timeout = random.uniform(self.ELECTION_TIMEOUT_MIN, self.ELECTION_TIMEOUT_MAX)
            self._heartbeat_event.clear()
            try:
                # Wake early if a heartbeat arrives; otherwise fire election.
                await asyncio.wait_for(
                    self._heartbeat_event.wait(),
                    timeout=timeout,
                )
                # Heartbeat received before timeout — loop back and reset.
            except asyncio.TimeoutError:
                elapsed = time.monotonic() - self.last_heartbeat
                logger.warning(
                    "Election timeout (%.2fs > %.2fs). Starting election for term %d",
                    elapsed,
                    timeout,
                    self.current_term + 1,
                )
                await self._start_election()

    async def _start_election(self):
        """Become Candidate and request votes."""
        self.role = NodeRole.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.last_heartbeat = time.monotonic()

        # In a real implementation, we would send RequestVote RPCs to peers
        # and track votes_received. For now, we simulate a single-node cluster
        # wins immediately if no peers, or just log the attempt for multi-node.

        if not self.peers:
            logger.info("No peers. Self-electing as LEADER.")
            await self._become_leader()
            return

        # TODO(raft): RequestVote RPC to peers; await majority → _become_leader()

    async def _become_leader(self) -> None:
        """Transition to Leader role."""
        if self.role == NodeRole.LEADER:
            return  # idempotent guard

        self.role = NodeRole.LEADER
        self.leader_id = self.node_id
        logger.info(
            "Node %s is now LEADER (Term %d)",
            self.node_id,
            self.current_term,
        )

        if self.state_callback:
            await self.state_callback(self.role)

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """Send heartbeats to followers."""
        while self._running and self.role == NodeRole.LEADER:
            # Stub: Send AppendEntries RPC (Heartbeat) to peers
            # logger.debug("Sending heartbeats...")

            # Update last_seen in DB for self
            await self._update_last_seen()

            await asyncio.sleep(self.HEARTBEAT_INTERVAL)

    async def _update_last_seen(self):
        """Update last_seen_at in cluster_nodes table."""
        try:
            await self.conn.execute(
                "UPDATE cluster_nodes SET last_seen_at = datetime('now'), "
                "raft_role = ? WHERE node_id = ?",
                (self.role.value, self.node_id),
            )
            await self.conn.commit()
        except (OSError, RuntimeError) as e:
            logger.error("Failed to update last_seen: %s", e)

    async def receive_heartbeat(self, leader_id: str, term: int):
        """Called when a heartbeat is received from the leader."""
        if term >= self.current_term:
            self.current_term = term
            self.leader_id = leader_id
            self.role = NodeRole.FOLLOWER
            self.last_heartbeat = time.monotonic()
            self._heartbeat_event.set()  # wake election_loop immediately
