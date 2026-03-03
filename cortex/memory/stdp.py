"""CORTEX v8 — Spike-Timing Dependent Plasticity (STDP).

Hebbian learning rule adapted for semantic graphs:
  "Neurons that fire together, wire together — but TIMING matters."

STDP modulates edge weights based on temporal co-activation ordering:
  - If A precedes B (causal) → LTP (strengthen connection)
  - If B precedes A (anti-causal) → LTD (weaken connection)

The weight change follows exponential decay within a time window,
producing temporally-sensitive co-activation patterns instead of
flat frequency counts.

Biological basis:
  - Pre → Post spike within 0-100ms → LTP (Long-Term Potentiation)
  - Post → Pre spike within 0-50ms → LTD (Long-Term Depression)
  - Beyond these windows → no change

Derivation: Ω₅ (Antifragile by Default) + Ω₁ (Multi-Scale Causality)
  → Edges evolve through temporal stress. Wrong-order patterns self-prune.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Final

logger = logging.getLogger("cortex.memory.stdp")

__all__ = ["STDPEngine", "SynapticEdge"]

# ─── Constants ────────────────────────────────────────────────────────

# LTP window: causal activations within this window strengthen
LTP_WINDOW_MS: Final[float] = 100.0

# LTD window: anti-causal activations within this window weaken
LTD_WINDOW_MS: Final[float] = 50.0

# Time constants for exponential decay
TAU_LTP: Final[float] = 20.0  # ms
TAU_LTD: Final[float] = 20.0  # ms

# Default learning rates
DEFAULT_LR_LTP: Final[float] = 0.05
DEFAULT_LR_LTD: Final[float] = 0.025

# Weight bounds
MIN_WEIGHT: Final[float] = 0.0
MAX_WEIGHT: Final[float] = 1.0

# Minimum weight before pruning
PRUNE_THRESHOLD: Final[float] = 0.01


# ─── Data Models ──────────────────────────────────────────────────────


@dataclass(slots=True)
class SynapticEdge:
    """A weighted, temporally-aware edge between two nodes.

    Tracks activation timestamps and applies STDP-based weight updates.
    """

    source_id: str
    target_id: str
    weight: float = 0.5
    last_updated: float = field(default_factory=time.monotonic)
    ltp_events: int = 0
    ltd_events: int = 0

    @property
    def plasticity_ratio(self) -> float:
        """LTP/LTD ratio — >1.0 means net strengthening."""
        total = self.ltp_events + self.ltd_events
        if total == 0:
            return 1.0
        return self.ltp_events / max(1, total)


# ─── STDP Engine ──────────────────────────────────────────────────────


class STDPEngine:
    """Spike-Timing Dependent Plasticity engine for semantic graphs.

    Modulates edge weights between concept nodes based on the temporal
    ordering of their activations. Integrates with CoAccessGraph to
    replace flat frequency-based edge updates.

    Usage:
        stdp = STDPEngine()

        # Record activations as they happen
        stdp.record_activation("python")
        # ... some time passes ...
        stdp.record_activation("tensorflow")

        # STDP automatically strengthens python→tensorflow edge (causal)
        # and weakens tensorflow→python edge (anti-causal)

        # Get edge weight
        weight = stdp.get_edge_weight("python", "tensorflow")

        # Periodic maintenance
        stdp.decay_all(factor=0.95)
    """

    __slots__ = (
        "_activations",
        "_edges",
        "_lr_ltp",
        "_lr_ltd",
        "_max_activations",
    )

    def __init__(
        self,
        lr_ltp: float = DEFAULT_LR_LTP,
        lr_ltd: float = DEFAULT_LR_LTD,
        max_activations: int = 4096,
    ) -> None:
        self._lr_ltp = lr_ltp
        self._lr_ltd = lr_ltd
        self._max_activations = max_activations

        # node_id → last activation timestamp (monotonic ms)
        self._activations: dict[str, float] = {}

        # (source, target) → SynapticEdge
        self._edges: dict[tuple[str, str], SynapticEdge] = {}

    def record_activation(self, node_id: str) -> list[tuple[str, str, float]]:
        """Record an activation event and apply STDP to all affected edges.

        Returns:
            List of (source_id, target_id, new_weight) for edges that changed.
        """
        now = time.monotonic() * 1000  # Convert to ms
        changes: list[tuple[str, str, float]] = []

        # Calculate delta_t with all recently-activated nodes
        for other_id, other_ts in self._activations.items():
            if other_id == node_id:
                continue

            delta_t = now - other_ts  # ms since other was activated

            if 0 < delta_t < LTP_WINDOW_MS:
                # other fired BEFORE current → causal (LTP: other→current)
                change = self._apply_ltp(other_id, node_id, delta_t)
                if change:
                    changes.append(change)

            elif -LTD_WINDOW_MS < delta_t < 0:
                # other fired AFTER current → anti-causal (LTD: current→other)
                change = self._apply_ltd(node_id, other_id, abs(delta_t))
                if change:
                    changes.append(change)

        # Record activation timestamp
        self._activations[node_id] = now

        # Bound activation history (Ω₂: Entropic Asymmetry)
        if len(self._activations) > self._max_activations:
            # Remove oldest third
            sorted_items = sorted(self._activations.items(), key=lambda x: x[1])
            cutoff = len(sorted_items) // 3
            for k, _ in sorted_items[:cutoff]:
                del self._activations[k]

        return changes

    def _apply_ltp(
        self, source_id: str, target_id: str, delta_t: float
    ) -> tuple[str, str, float] | None:
        """Apply Long-Term Potentiation (strengthen causal edge).

        Weight increase follows: lr * exp(-delta_t / tau)
        """
        weight_increase = self._lr_ltp * math.exp(-delta_t / TAU_LTP)

        edge_key = (source_id, target_id)
        edge = self._edges.get(edge_key)

        if edge is None:
            # Create new edge with initial weight + LTP boost
            edge = SynapticEdge(
                source_id=source_id,
                target_id=target_id,
                weight=min(MAX_WEIGHT, 0.1 + weight_increase),
            )
            self._edges[edge_key] = edge
        else:
            edge.weight = min(MAX_WEIGHT, edge.weight + weight_increase)
            edge.last_updated = time.monotonic()

        edge.ltp_events += 1

        if weight_increase > 0.001:
            logger.debug(
                "STDP LTP: %s→%s (Δt=%.1fms, Δw=+%.4f, w=%.4f)",
                source_id,
                target_id,
                delta_t,
                weight_increase,
                edge.weight,
            )

        return (source_id, target_id, edge.weight)

    def _apply_ltd(
        self, source_id: str, target_id: str, delta_t: float
    ) -> tuple[str, str, float] | None:
        """Apply Long-Term Depression (weaken anti-causal edge).

        Weight decrease follows: lr * exp(-delta_t / tau_ltd)
        """
        edge_key = (source_id, target_id)
        edge = self._edges.get(edge_key)

        if edge is None:
            # No existing edge to weaken — skip
            return None

        weight_decrease = self._lr_ltd * math.exp(-delta_t / TAU_LTD)
        edge.weight = max(MIN_WEIGHT, edge.weight - weight_decrease)
        edge.last_updated = time.monotonic()
        edge.ltd_events += 1

        if weight_decrease > 0.001:
            logger.debug(
                "STDP LTD: %s→%s (Δt=%.1fms, Δw=-%.4f, w=%.4f)",
                source_id,
                target_id,
                delta_t,
                weight_decrease,
                edge.weight,
            )

        return (source_id, target_id, edge.weight)

    def get_edge_weight(self, source_id: str, target_id: str) -> float:
        """Get current weight of an edge. Returns 0.0 if no edge exists."""
        edge = self._edges.get((source_id, target_id))
        return edge.weight if edge else 0.0

    def get_edge(self, source_id: str, target_id: str) -> SynapticEdge | None:
        """Get full edge metadata."""
        return self._edges.get((source_id, target_id))

    def strongest_successors(self, node_id: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Return the strongest outgoing edges from a node.

        Returns list of (target_id, weight) sorted by weight descending.
        """
        successors: list[tuple[str, float]] = []
        for (src, tgt), edge in self._edges.items():
            if src == node_id and edge.weight > PRUNE_THRESHOLD:
                successors.append((tgt, edge.weight))
        successors.sort(key=lambda x: x[1], reverse=True)
        return successors[:top_k]

    def decay_all(self, factor: float = 0.95) -> int:
        """Apply global temporal decay to all edges.

        Returns number of edges pruned (weight below threshold).
        """
        pruned = 0
        to_remove: list[tuple[str, str]] = []

        for key, edge in self._edges.items():
            edge.weight *= factor
            if edge.weight < PRUNE_THRESHOLD:
                to_remove.append(key)

        for key in to_remove:
            del self._edges[key]
            pruned += 1

        if pruned:
            logger.info("STDP decay: pruned %d sub-threshold edges", pruned)

        return pruned

    # ─── Introspection ────────────────────────────────────────────

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    @property
    def node_count(self) -> int:
        nodes: set[str] = set()
        for src, tgt in self._edges:
            nodes.add(src)
            nodes.add(tgt)
        return len(nodes)

    def status(self) -> dict[str, Any]:
        """STDP engine health dashboard."""
        total_ltp = sum(e.ltp_events for e in self._edges.values())
        total_ltd = sum(e.ltd_events for e in self._edges.values())
        avg_weight = (
            sum(e.weight for e in self._edges.values()) / len(self._edges) if self._edges else 0.0
        )
        return {
            "edges": self.edge_count,
            "nodes": self.node_count,
            "activations_tracked": len(self._activations),
            "total_ltp_events": total_ltp,
            "total_ltd_events": total_ltd,
            "avg_edge_weight": round(avg_weight, 4),
            "plasticity_ratio": round(total_ltp / max(1, total_ltp + total_ltd), 4),
        }

    def __repr__(self) -> str:
        return (
            f"STDPEngine(edges={self.edge_count}, nodes={self.node_count}, "
            f"lr_ltp={self._lr_ltp}, lr_ltd={self._lr_ltd})"
        )
