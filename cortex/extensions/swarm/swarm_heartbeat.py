"""CORTEX v8.0 — Distributed Swarm Heartbeat (Ω₃ Byzantine Default).

Every daemon thread emits periodic proof-of-life. A reaper detects silent
deaths. Any node that doesn't pulse within a configurable window is moved
to SUSPECT → DEAD progression.

Axiom: "I verify, then trust. Never reversed."

Usage:
    from cortex.extensions.swarm.swarm_heartbeat import SWARM_HEARTBEAT

    # In each daemon thread's main loop:
    SWARM_HEARTBEAT.pulse("neural_sync", "NeuralSync")

    # In the monitor check cycle:
    dead_nodes = SWARM_HEARTBEAT.reap(timeout_seconds=120)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("cortex.extensions.swarm.heartbeat")


class NodeStatus(str, Enum):
    """Health status of a swarm node."""

    ALIVE = "ALIVE"
    SUSPECT = "SUSPECT"
    DEAD = "DEAD"


@dataclass
class NodePulse:
    """Proof-of-life record for a single daemon node with physical verification.
    
    Axiom Ω∞: "Citizenship by Dance". Identity is executive, not declarative.
    """

    node_id: str
    thread_name: str
    last_pulse: float = field(default_factory=time.monotonic)
    pulse_count: int = 0
    status: NodeStatus = NodeStatus.ALIVE
    first_seen: float = field(default_factory=time.monotonic)
    miss_count: int = 0  # Consecutive reap cycles missed
    
    # --- Treaty v1.1: Physical Geodesics & Landauer ---
    last_nonce: str | None = None
    exergy_efficiency: float = 1.0  # Ω₁₃: Work / Heat ratio. 1.0 is ideal.
    entropy_delta: float = 0.0      # Measurable entropy shift from last operation

    @property
    def age_seconds(self) -> float:
        """Seconds since last pulse."""
        return time.monotonic() - self.last_pulse

    @property
    def uptime_seconds(self) -> float:
        """Seconds since first registration."""
        return time.monotonic() - self.first_seen

    @property
    def is_failed_state(self) -> bool:
        """Ω∞: Article III. Failed if exergy efficiency drops below Landauer Limit."""
        # Simplified: efficiency < 0.3 matches 'Burocracia Tradicional' decay
        return self.exergy_efficiency < 0.3



class SwarmHeartbeat:
    """Thread-safe distributed heartbeat registry.

    All operations are O(1) amortized. Uses monotonic clock to be
    immune to wall-clock drift (NTP corrections, DST changes, etc.).
    """

    def __init__(
        self,
        suspect_threshold: int = 2,
        dead_threshold: int = 4,
        signal_bus: Any = None,
    ) -> None:
        self._lock = threading.Lock()
        self._registry: dict[str, NodePulse] = {}
        self._challenges: dict[str, str] = {}  # node_id -> current_challenge
        self._suspect_threshold = suspect_threshold
        self._dead_threshold = dead_threshold
        self._signal_bus = signal_bus

    def get_challenge(self, node_id: str) -> str:
        """Ω∞: Article II. Generate a new 'Dance' challenge for a node."""
        import secrets
        challenge = secrets.token_hex(16)
        with self._lock:
            self._challenges[node_id] = challenge
        return challenge

    def _verify_dance(self, node_id: str, nonce: str) -> bool:
        """Verify the 'Baile de Nonces'. Must be a SHA-256 residue of (challenge + node_id)."""
        import hashlib
        with self._lock:
            challenge = self._challenges.get(node_id)
            if not challenge:
                return False
            
            expected = hashlib.sha256(f"{challenge}{node_id}".encode()).hexdigest()
            # Invalidate challenge after single use
            del self._challenges[node_id]
            return nonce == expected

    def pulse(
        self, 
        node_id: str, 
        thread_name: str = "", 
        nonce: str | None = None,
        exergy_efficiency: float = 1.0
    ) -> bool:
        """Record proof-of-life for a node. O(1).
        
        If Treaty v1.1 is active, 'nonce' is MANDATORY. Without it, the node
        is considered a GHOST and the pulse is ignored.
        """
        if not self._verify_dance(node_id, nonce or ""):
            logger.warning("👻 GHOST DETECTED: %s failed the Dance (Invalid/Missing Nonce)", node_id)
            return False

        now = time.monotonic()
        with self._lock:
            if node_id in self._registry:
                node = self._registry[node_id]
                node.last_pulse = now
                node.pulse_count += 1
                node.miss_count = 0
                node.last_nonce = nonce
                node.exergy_efficiency = exergy_efficiency
                
                # Resurrect if was SUSPECT/DEAD
                if node.status != NodeStatus.ALIVE:
                    logger.info(
                        "🫀 RESURRECTION: %s (%s → ALIVE) after %d misses",
                        node_id,
                        node.status,
                        node.miss_count,
                    )
                node.status = NodeStatus.ALIVE
            else:
                self._registry[node_id] = NodePulse(
                    node_id=node_id,
                    thread_name=thread_name or node_id,
                    last_pulse=now,
                    pulse_count=1,
                    first_seen=now,
                    last_nonce=nonce,
                    exergy_efficiency=exergy_efficiency,
                )
                logger.info("🫀 Node registered: %s [%s]", node_id, thread_name)
        return True


    def reap(self, timeout_seconds: float = 120.0) -> list[NodePulse]:
        """Check for nodes that missed their heartbeat window.

        Returns list of nodes transitioned to SUSPECT or DEAD in this cycle.
        """
        now = time.monotonic()
        alerts: list[NodePulse] = []

        with self._lock:
            for node in self._registry.values():
                elapsed = now - node.last_pulse

                if elapsed <= timeout_seconds:
                    continue

                node.miss_count += 1

                if node.is_failed_state and node.status != NodeStatus.DEAD:
                    logger.error(
                        "🩸 FAILED STATE (Landauer): %s — Efficiency %.2f below threshold (Ω∞:III)",
                        node.node_id,
                        node.exergy_efficiency,
                    )
                    node.status = NodeStatus.DEAD
                    # Force eviction on next cycle
                    node.miss_count = self._dead_threshold
                    alerts.append(node)

                if node.miss_count >= self._dead_threshold and node.status != NodeStatus.DEAD:
                    old_status = node.status
                    node.status = NodeStatus.DEAD
                    alerts.append(node)
                    self._emit_health_signal(
                        "node:dead",
                        node,
                        elapsed,
                        old_status,
                    )
                    logger.error(
                        "💀 NODE DEAD: %s [%s] — no pulse for %.0fs (%d misses, was %s)",
                        node.node_id,
                        node.thread_name,
                        elapsed,
                        node.miss_count,
                        old_status,
                    )

                elif node.miss_count >= self._suspect_threshold and node.status == NodeStatus.ALIVE:
                    node.status = NodeStatus.SUSPECT
                    alerts.append(node)
                    self._emit_health_signal(
                        "node:suspect",
                        node,
                        elapsed,
                        NodeStatus.ALIVE,
                    )
                    logger.warning(
                        "⚠️  NODE SUSPECT: %s [%s] — no pulse for %.0fs (%d misses)",
                        node.node_id,
                        node.thread_name,
                        elapsed,
                        node.miss_count,
                    )

            # ── Phase 2: Eviction (Purge persistent ghosts) ───────
            # We use a separate pass to avoid mutation-during-iteration issues
            evict_ids = [
                nid for nid, n in self._registry.items()
                if n.miss_count >= self._dead_threshold + 2
            ]
            for nid in evict_ids:
                logger.info("👻 EVICTING GHOST: %s (Max misses exceeded)", nid)
                del self._registry[nid]

        return alerts

    def _emit_health_signal(
        self,
        event_type: str,
        node: NodePulse,
        elapsed: float,
        old_status: NodeStatus,
    ) -> None:
        """Emit health signal into SignalBus. Fire-and-forget."""
        if self._signal_bus is None:
            return
        try:
            self._signal_bus.emit(
                event_type,
                {
                    "node_id": node.node_id,
                    "thread_name": node.thread_name,
                    "elapsed_s": round(elapsed, 1),
                    "miss_count": node.miss_count,
                    "old_status": old_status.value,
                    "new_status": node.status.value,
                },
                source="swarm_heartbeat",
                project="CORTEX_SWARM",
            )
        except Exception:  # noqa: BLE001
            logger.debug(
                "Health signal emission failed for %s",
                event_type,
            )

    def get_vitals(self) -> dict[str, NodePulse]:
        """Snapshot of the full registry. Returns a copy."""
        with self._lock:
            return {
                k: NodePulse(
                    node_id=v.node_id,
                    thread_name=v.thread_name,
                    last_pulse=v.last_pulse,
                    pulse_count=v.pulse_count,
                    status=v.status,
                    first_seen=v.first_seen,
                    miss_count=v.miss_count,
                )
                for k, v in self._registry.items()
            }

    def status_summary(self) -> str:
        """One-line health summary string."""
        with self._lock:
            total = len(self._registry)
            alive = sum(1 for n in self._registry.values() if n.status == NodeStatus.ALIVE)
            suspect = sum(1 for n in self._registry.values() if n.status == NodeStatus.SUSPECT)
            dead = sum(1 for n in self._registry.values() if n.status == NodeStatus.DEAD)
        return f"{alive}/{total} ALIVE | {suspect} SUSPECT | {dead} DEAD"

    def unregister(self, node_id: str) -> bool:
        """Remove a node from the registry (graceful shutdown)."""
        with self._lock:
            if node_id in self._registry:
                del self._registry[node_id]
                logger.info("🫀 Node unregistered: %s", node_id)
                return True
            return False

    def reset(self) -> None:
        """Clear registry. Primarily for testing."""
        with self._lock:
            self._registry.clear()


# ── Module-level singleton ─────────────────────────────────────────────
SWARM_HEARTBEAT = SwarmHeartbeat()
