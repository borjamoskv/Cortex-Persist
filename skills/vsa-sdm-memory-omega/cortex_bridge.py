"""
CORTEX Swarm ↔ VSA Memory Bridge v1.0
Connects the VSA-SDM engine to the CORTEX-Swarm-Prime agent lifecycle.

Replaces the text-based Episodic Memory (Hot/Warm/Cold YAML cache)
with algebraic context collapse for the Warm and Cold layers.

Usage by Swarm agents:
    from cortex_bridge import SwarmMemory

    mem = SwarmMemory(agent_id="centurion-042")
    mem.record_action("deployed api v2 to staging", tags={"env": "staging"})
    mem.record_action("scaled workers to 10", tags={"count": "10"})

    # Retrieve what this agent did regarding deployment
    result = mem.recall_by_text("deploy")

    # Consolidate to ledger (persist to disk)
    mem.consolidate()

    # Cross-agent memory: query another agent's tensor
    mem.load_agent("centurion-099")
"""
import os
import time
from pathlib import Path

from vsa_engine import VSAEngine


# Default memory directory
MEMORY_DIR = Path.home() / ".cortex" / "memory" / "vsa"


class SwarmMemory:
    """Per-agent VSA memory with swarm-level federation."""

    def __init__(self, agent_id, D=10000, decay_lambda=0.05,
                 memory_dir=None):
        """
        Args:
            agent_id: Unique agent identifier within the swarm.
            D: Hypervector dimensionality.
            decay_lambda: Ebbinghaus decay rate (0 = no decay).
            memory_dir: Override for .vsa file storage.
        """
        self.agent_id = agent_id
        self.decay_lambda = decay_lambda
        self.memory_dir = Path(memory_dir or MEMORY_DIR)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Each agent gets a deterministic seed based on its ID
        seed = hash(agent_id) % (2**31)
        self.engine = VSAEngine(D=D, algebra="HRR", seed=seed)

        # Action log for structured retrieval
        self._action_log = []

        # Try to load existing memory
        vsa_path = self._vsa_path()
        if vsa_path.exists():
            try:
                self.engine.load(str(vsa_path))
            except ValueError:
                pass  # Corrupted file, start fresh

    def _vsa_path(self, agent_id=None):
        aid = agent_id or self.agent_id
        return self.memory_dir / f"{aid}.vsa"

    # ── Recording ──

    def record_action(self, description, tags=None, timestamp=None):
        """
        Record an agent action into the VSA memory tensor.

        Args:
            description: Free-text description of the action.
            tags: Optional dict of structured metadata.
            timestamp: Unix timestamp (default: now).
        """
        ts = timestamp or time.time()

        # Generate a time-key for this event
        time_key = self.engine.random_vec()

        # Encode the action as a hybrid hypervector
        text_vec = self.engine.encode_text(description)
        if tags:
            record_vec = self.engine.encode_record(tags)
            # Bundle text and structured encodings
            state_vec = self.engine.bundle([text_vec, record_vec])
        else:
            state_vec = text_vec

        # Memorize with decay
        self.engine.memorize(
            time_key, state_vec,
            timestamp=ts,
            decay_lambda=self.decay_lambda
        )

        # Keep structured log for codebook-based retrieval
        self._action_log.append({
            "key": time_key,
            "state": state_vec,
            "text": description,
            "tags": tags or {},
            "timestamp": ts,
        })

    def record_state(self, state_dict, timestamp=None):
        """
        Record a full agent state snapshot (structured).
        Useful for periodic checkpoints.
        """
        ts = timestamp or time.time()
        time_key = self.engine.random_vec()
        state_vec = self.engine.encode_record(state_dict)
        self.engine.memorize(
            time_key, state_vec,
            timestamp=ts,
            decay_lambda=self.decay_lambda
        )
        self._action_log.append({
            "key": time_key,
            "state": state_vec,
            "text": str(state_dict),
            "tags": state_dict,
            "timestamp": ts,
        })

    # ── Retrieval ──

    def recall_by_text(self, query_text, top_k=3):
        """
        Find the most similar stored actions to a text query.
        Uses cosine similarity against stored state vectors.

        Returns list of (similarity, text, tags, timestamp).
        """
        query_vec = self.engine.encode_text(query_text)
        results = []
        for entry in self._action_log:
            sim = self.engine.cosine(query_vec, entry["state"])
            results.append((
                sim,
                entry["text"],
                entry["tags"],
                entry["timestamp"],
            ))
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]

    def recall_by_key(self, time_key):
        """Direct VSA unbind retrieval using a known time-key."""
        return self.engine.recall(time_key)

    # ── Lifecycle ──

    def consolidate(self):
        """
        Persist memory tensor to disk (.vsa binary + SHA-256).
        This is the swarm equivalent of '/swarm-prime consolidate'.
        """
        # Apply forgetting first
        purged = self.engine.forget(epsilon=0.01)
        # Save
        path = self._vsa_path()
        size = self.engine.save(str(path))
        return {
            "agent": self.agent_id,
            "path": str(path),
            "bytes": size,
            "items": self.engine.item_count,
            "purged": purged,
            "snr": self.engine.snr,
        }

    def load_agent(self, other_agent_id):
        """
        Load another agent's memory tensor for cross-agent queries.
        Returns a new VSAEngine with that agent's memory loaded.
        """
        path = self._vsa_path(other_agent_id)
        if not path.exists():
            raise FileNotFoundError(
                f"No memory for agent {other_agent_id}"
            )
        other = VSAEngine(D=self.engine.D, seed=0)
        other.load(str(path))
        return other

    def diagnostics(self):
        """Return memory diagnostics for swarm health dashboard."""
        report = self.engine.capacity_report()
        report["agent_id"] = self.agent_id
        report["actions_logged"] = len(self._action_log)
        report["decay_lambda"] = self.decay_lambda
        report["persisted"] = self._vsa_path().exists()
        return report


# ── Swarm-Level Operations ──

def federation_merge(agent_memories, weights=None):
    """
    Merge multiple agent memory tensors into a swarm-level
    collective memory. Each agent's tensor is weighted and bundled.

    Args:
        agent_memories: List of SwarmMemory instances.
        weights: Optional per-agent weights (default: equal).

    Returns:
        A new VSAEngine containing the merged memory.
    """
    if not agent_memories:
        raise ValueError("No agents to merge")

    D = agent_memories[0].engine.D
    if weights is None:
        weights = [1.0 / len(agent_memories)] * len(agent_memories)

    merged = VSAEngine(D=D, seed=0)
    merged.memory = sum(
        w * m.engine.memory
        for w, m in zip(weights, agent_memories)
    )
    merged.memory = merged.normalize(merged.memory)
    return merged
