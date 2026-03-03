"""
CORTEX v5.0 — Raft Consensus Implementation.

Handles leader election and log replication state.
"""

import asyncio
import logging
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum

import aiosqlite

__all__ = ["NodeRole", "PreVoteResult", "RaftNode", "NodeRegistry"]

logger = logging.getLogger(__name__)

_rng = secrets.SystemRandom()


class NodeRole(Enum):
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"


@dataclass(slots=True, frozen=True)
class PreVoteResult:
    """Result of the pre-vote phase."""

    granted: int  # peers that would grant a vote
    total: int  # peers contacted

    @property
    def quorum_reachable(self) -> bool:
        """True if a majority (self + granted peers) would win a real election."""
        cluster_size = self.total + 1  # +1 for self-vote
        needed = cluster_size // 2 + 1
        return (self.granted + 1) >= needed


# ─── In-Process Node Registry ─────────────────────────────────────────────────
# Shared dict mapping node_id → RaftNode for same-process clusters.
# For multi-process clusters, replace RequestVote with HTTP/gRPC calls.


class NodeRegistry:
    """In-process singleton registry for RaftNode instances.

    Intentionally uses a class-level dict: all callers in the same process
    must share the same view of the cluster topology.
    """

    _nodes: dict[str, "RaftNode"] = {}

    @classmethod
    def register(cls, node: "RaftNode") -> None:
        cls._nodes[node.node_id] = node

    @classmethod
    def deregister(cls, node_id: str) -> None:
        cls._nodes.pop(node_id, None)

    @classmethod
    def get(cls, node_id: str) -> "RaftNode | None":
        return cls._nodes.get(node_id)

    @classmethod
    def reset(cls) -> None:
        """Clear all registrations. Use in tests for isolation."""
        cls._nodes.clear()


# ─── RaftNode ─────────────────────────────────────────────────────────────────


class RaftNode:
    """
    Raft Consensus Node — Phase 2: Full Leader Election (RequestVote RPC).

    Manages node state, election timeouts, and role transitions.
    Supports both in-process clusters (NodeRegistry) and stub peer resolution.
    """

    HEARTBEAT_INTERVAL = 1.0  # seconds
    ELECTION_TIMEOUT_MIN = 1.5  # seconds (tightened from 3.0 for faster convergence)
    ELECTION_TIMEOUT_MAX = 3.0  # seconds

    # Pre-vote phase (Ongaro §9.6): candidate probes peers BEFORE
    # incrementing current_term. Eliminates term inflation caused by
    # partitioned nodes looping through elections with no quorum.
    PRE_VOTE_ENABLED = True

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
        self._heartbeat_event = asyncio.Event()
        self._role_lock = asyncio.Lock()

        NodeRegistry.register(self)

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
                    pass  # Expected — do NOT re-raise during shutdown
        self._election_task = None
        self._heartbeat_task = None
        NodeRegistry.deregister(self.node_id)
        logger.info("RaftNode %s stopped", self.node_id)

    async def _election_loop(self):
        """Monitor heartbeat and trigger elections using event-driven sleep.

        Instead of polling every 0.1s, we sleep exactly until the randomised
        election timeout expires. A heartbeat arrival wakes us early via
        _heartbeat_event, resetting the wait.
        """
        while self._running:
            if self.role == NodeRole.LEADER:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                continue

            timeout = _rng.uniform(self.ELECTION_TIMEOUT_MIN, self.ELECTION_TIMEOUT_MAX)
            self._heartbeat_event.clear()
            try:
                await asyncio.wait_for(
                    self._heartbeat_event.wait(),
                    timeout=timeout,
                )
                # Heartbeat received — reset loop
            except asyncio.TimeoutError:
                if self._heartbeat_event.is_set():
                    continue

                elapsed = time.monotonic() - self.last_heartbeat
                logger.warning(
                    "Election timeout (%.2fs > %.2fs). Starting election for term %d",
                    elapsed,
                    timeout,
                    self.current_term + 1,
                )
                # Acquire lock only for the initial role transition, then release.
                should_elect = False
                async with self._role_lock:
                    if self.role == NodeRole.FOLLOWER:
                        should_elect = True
                if should_elect:
                    await self._start_election()

    async def _pre_vote(self) -> PreVoteResult:
        """Pre-vote phase (Ongaro §9.6).

        Broadcast a *hypothetical* RequestVote for (current_term + 1) WITHOUT
        persisting any state change.  A peer grants a pre-vote if:
          - It hasn't heard from a valid leader recently (election timeout elapsed)
          - The hypothetical term >= its own current_term

        This prevents partitioned nodes from inflating the cluster term with
        elections that could never achieve majority.
        """
        if not self.peers:
            return PreVoteResult(granted=0, total=0)

        hypothetical_term = self.current_term + 1

        async def _ask_peer(peer_id: str) -> bool:
            peer = NodeRegistry.get(peer_id)
            if peer is None:
                logger.debug("PreVote: peer %s not in registry, counting as deny.", peer_id)
                return False
            return await peer.handle_pre_vote_request(
                candidate_id=self.node_id,
                hypothetical_term=hypothetical_term,
            )

        results = await asyncio.gather(
            *(_ask_peer(p) for p in self.peers),
            return_exceptions=True,
        )
        granted = sum(1 for r in results if r is True)
        logger.debug(
            "PreVote result: %d/%d peers would grant for hypothetical term %d",
            granted,
            len(self.peers),
            hypothetical_term,
        )
        return PreVoteResult(granted=granted, total=len(self.peers))

    async def handle_pre_vote_request(self, candidate_id: str, hypothetical_term: int) -> bool:
        """Handle an incoming PreVote RPC.

        Grant pre-vote if:
          - hypothetical_term >= our current_term
          - We haven't heard from a valid leader recently (election timeout elapsed)

        CRITICAL: This method does NOT mutate any state (term, voted_for, role).
        """
        async with self._role_lock:
            if hypothetical_term < self.current_term:
                return False

            # Only grant if we also think the leader might be dead
            elapsed = time.monotonic() - self.last_heartbeat
            leader_alive = elapsed < self.ELECTION_TIMEOUT_MIN
            if leader_alive:
                logger.debug(
                    "PreVote deny to %s: leader still alive (%.2fs < %.2fs)",
                    candidate_id,
                    elapsed,
                    self.ELECTION_TIMEOUT_MIN,
                )
                return False

            return True

    async def _start_election(self) -> None:
        """Become Candidate, broadcast RequestVote RPC and tally majority.

        Must be called WITHOUT holding _role_lock.
        _role_lock is acquired atomically per-transition, then released.
        """
        # ─── Pre-vote gate ─────────────────────────────────────────────────
        if self.PRE_VOTE_ENABLED and self.peers:
            pre = await self._pre_vote()
            if not pre.quorum_reachable:
                logger.warning(
                    "Pre-vote failed: quorum unreachable (%d/%d peers would grant). "
                    "Aborting election to prevent term inflation.",
                    pre.granted,
                    pre.total,
                )
                return  # Stay FOLLOWER; election_loop re-samples timeout
            logger.info(
                "Pre-vote passed (%d/%d). Proceeding to real election.",
                pre.granted,
                pre.total,
            )

        # ─── Atomic transition to CANDIDATE ────────────────────────────────
        async with self._role_lock:
            if self.role != NodeRole.FOLLOWER:
                return  # Already mutated by another path
            self.role = NodeRole.CANDIDATE
            self.current_term += 1
            self.voted_for = self.node_id
            self.last_heartbeat = time.monotonic()
            term = self.current_term
        # Lock released — RPCs happen without holding it
        logger.info(
            "Node %s starting election for term %d (peers=%s)",
            self.node_id,
            term,
            self.peers,
        )

        if not self.peers:
            # Single-node cluster: win immediately
            logger.info("No peers. Self-electing as LEADER.")
            await self._become_leader()
            return

        # ─── RequestVote RPC ───────────────────────────────────────────────
        votes_received = 1  # Self-vote counts
        majority = (len(self.peers) + 1) // 2 + 1  # +1 for self

        vote_tasks = [asyncio.create_task(self._request_vote(peer, term)) for peer in self.peers]

        # Race for majority within one election timeout window
        vote_timeout = _rng.uniform(self.ELECTION_TIMEOUT_MIN, self.ELECTION_TIMEOUT_MAX)

        try:
            done, pending = await asyncio.wait(
                vote_tasks,
                timeout=vote_timeout,
                return_when=asyncio.ALL_COMPLETED,
            )
        except asyncio.CancelledError:
            for t in vote_tasks:
                t.cancel()
            raise

        for t in pending:
            t.cancel()

        for task in done:
            try:
                granted = task.result()
                if granted:
                    votes_received += 1
            except Exception as exc:
                logger.debug("Vote request failed: %s", exc)

        # If term changed while we were voting (split-brain / higher term), abort
        if self.current_term != term or self.role != NodeRole.CANDIDATE:
            logger.info("Election aborted for term %d: term changed or role mutated.", term)
            return

        logger.info(
            "Term %d election result: %d/%d votes (majority=%d)",
            term,
            votes_received,
            len(self.peers) + 1,
            majority,
        )

        if votes_received >= majority:
            await self._become_leader()
        else:
            # Didn't win — revert to FOLLOWER and wait for next timeout
            async with self._role_lock:
                self.role = NodeRole.FOLLOWER
            logger.info(
                "Node %s lost election for term %d. Reverting to FOLLOWER.", self.node_id, term
            )

    async def _request_vote(self, peer_id: str, term: int) -> bool:
        """Send RequestVote RPC to a peer.

        Tries in-process NodeRegistry first (same-runtime cluster).
        For multi-process, this is where the HTTP/gRPC call would go.

        Returns True if vote was granted, False otherwise.
        """
        peer = NodeRegistry.get(peer_id)
        if peer is None:
            # Peer not in registry — could be remote (stub: assume no vote)
            logger.debug("Peer %s not in NodeRegistry. Skipping vote.", peer_id)
            return False

        granted = await peer.handle_vote_request(
            candidate_id=self.node_id,
            candidate_term=term,
        )
        logger.debug(
            "RequestVote(%s → %s, term=%d): %s",
            self.node_id,
            peer_id,
            term,
            "GRANTED" if granted else "DENIED",
        )
        return granted

    async def handle_vote_request(self, candidate_id: str, candidate_term: int) -> bool:
        """Handle an incoming RequestVote RPC (called by the candidate on this node).

        Grants vote if:
          - candidate_term >= our current term
          - We haven't voted in this term yet (or already voted for this candidate)
        """
        async with self._role_lock:
            # Higher term: update our term and revert to FOLLOWER
            if candidate_term > self.current_term:
                self.current_term = candidate_term
                self.voted_for = None
                self.role = NodeRole.FOLLOWER

            if candidate_term < self.current_term:
                logger.debug(
                    "Denying vote to %s: stale term %d < %d",
                    candidate_id,
                    candidate_term,
                    self.current_term,
                )
                return False

            already_voted = self.voted_for is not None and self.voted_for != candidate_id
            if already_voted:
                logger.debug(
                    "Denying vote to %s: already voted for %s in term %d",
                    candidate_id,
                    self.voted_for,
                    self.current_term,
                )
                return False

            # Grant vote
            self.voted_for = candidate_id
            self.last_heartbeat = time.monotonic()
            self._heartbeat_event.set()  # Reset election timer on this node too
            logger.info(
                "Node %s GRANTED vote to %s for term %d",
                self.node_id,
                candidate_id,
                candidate_term,
            )
            return True

    async def _become_leader(self) -> None:
        """Transition to Leader role."""
        async with self._role_lock:
            if self.role == NodeRole.LEADER:
                return  # idempotent guard

            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass

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

    async def _heartbeat_loop(self) -> None:
        """Send heartbeats to followers."""
        while self._running and self.role == NodeRole.LEADER:
            await self._update_last_seen()
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)

    async def _update_last_seen(self) -> None:
        """Update last_seen_at in cluster_nodes table."""
        try:
            await self.conn.execute(
                "UPDATE cluster_nodes SET last_seen_at = datetime('now'), "
                "raft_role = ? WHERE node_id = ?",
                (self.role.value, self.node_id),
            )
            await self.conn.commit()
        except (OSError, RuntimeError, aiosqlite.OperationalError) as e:
            logger.error("Failed to update last_seen for %s: %s", self.node_id, e)

    async def receive_heartbeat(self, leader_id: str, term: int) -> None:
        """Called when a heartbeat is received from the leader."""
        async with self._role_lock:
            if term >= self.current_term:
                self.current_term = term
                self.leader_id = leader_id

                if self.role != NodeRole.FOLLOWER:
                    logger.info(
                        "Node %s stepping down to FOLLOWER (leader=%s, term=%d).",
                        self.node_id,
                        leader_id,
                        term,
                    )
                    if self._heartbeat_task and not self._heartbeat_task.done():
                        self._heartbeat_task.cancel()
                    self.role = NodeRole.FOLLOWER

                self.last_heartbeat = time.monotonic()
                self._heartbeat_event.set()
