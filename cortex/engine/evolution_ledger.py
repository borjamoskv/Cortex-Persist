# [C5-REAL] Exergy-Maximized
"""
Evolution Ledger Layer — Replay-Safe Substrate Mutation Log.

Axiom Reference:
- Ω₃ (Byzantine Default): Every control vector mutation is hash-chained.
- Ω₂ (Entropic Asymmetry): Performance deltas form a replayable audit trail.

Architecture:
    update_control_vector() → EvolutionLedger.record_mutation()
                                    ↓
                              hash_chain(prev_hash, mutation_payload)
                                    ↓
                              append-only JSONL log + optional SovereignLedger bridge

    replay() → reads JSONL, verifies hash chain, reconstructs substrate state.

This module is the SINGLE source of truth for substrate evolution history.
It does NOT depend on SQLite — it uses append-only JSONL for maximum
portability and crash-safety (each line is atomic on POSIX fsync).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import struct
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger("cortex.evolution_ledger")

__all__ = [
    "EvolutionLedger",
    "MutationRecord",
    "ReplayVerificationError",
]


# ─── Data Structures ─────────────────────────────────────────────


@dataclass(frozen=True)
class ControlVector:
    """Snapshot of the 4-scalar UESS v2 control vector."""

    queue_depth: float
    error_rate: float
    causal_entropy: float
    cpu_load: float

    def to_bytes(self) -> bytes:
        return struct.pack("dddd", self.queue_depth, self.error_rate,
                           self.causal_entropy, self.cpu_load)

    def magnitude(self) -> float:
        return (self.queue_depth**2 + self.error_rate**2 +
                self.causal_entropy**2 + self.cpu_load**2) ** 0.5

    def delta(self, other: ControlVector) -> ControlVector:
        return ControlVector(
            queue_depth=self.queue_depth - other.queue_depth,
            error_rate=self.error_rate - other.error_rate,
            causal_entropy=self.causal_entropy - other.causal_entropy,
            cpu_load=self.cpu_load - other.cpu_load,
        )


@dataclass
class MutationRecord:
    """A single hash-chained mutation event."""

    sequence: int
    agent_idx: int
    timestamp: float
    prev_hash: str
    hash: str
    vector_before: ControlVector | None
    vector_after: ControlVector
    performance_delta: float | None  # ops/sec delta if benchmark is active
    source: str  # caller identity: "substrate", "evolution_engine", "manual"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "seq": self.sequence,
            "agent_idx": self.agent_idx,
            "ts": self.timestamp,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
            "vector_after": {
                "queue_depth": self.vector_after.queue_depth,
                "error_rate": self.vector_after.error_rate,
                "causal_entropy": self.vector_after.causal_entropy,
                "cpu_load": self.vector_after.cpu_load,
            },
            "source": self.source,
        }
        if self.vector_before is not None:
            d["vector_before"] = {
                "queue_depth": self.vector_before.queue_depth,
                "error_rate": self.vector_before.error_rate,
                "causal_entropy": self.vector_before.causal_entropy,
                "cpu_load": self.vector_before.cpu_load,
            }
        if self.performance_delta is not None:
            d["perf_delta"] = self.performance_delta
        if self.metadata:
            d["meta"] = self.metadata
        return d

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> MutationRecord:
        va = payload["vector_after"]
        vb = payload.get("vector_before")
        return cls(
            sequence=payload["seq"],
            agent_idx=payload["agent_idx"],
            timestamp=payload["ts"],
            prev_hash=payload["prev_hash"],
            hash=payload["hash"],
            vector_before=ControlVector(**vb) if vb else None,
            vector_after=ControlVector(**va),
            performance_delta=payload.get("perf_delta"),
            source=payload["source"],
            metadata=payload.get("meta", {}),
        )


class ReplayVerificationError(Exception):
    """Hash chain integrity violation during replay."""
    pass


# ─── Canonical Hash ───────────────────────────────────────────────


def _canonical_json(obj: Any) -> str:
    """Deterministic JSON — matches cortex.utils.canonical.canonical_json."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, default=str)


def _compute_mutation_hash(
    prev_hash: str,
    sequence: int,
    agent_idx: int,
    timestamp: float,
    vector_after: ControlVector,
    source: str,
) -> str:
    """Compute SHA-256 hash for a mutation record.
    
    Format: v1\x00{prev}\x00{seq}\x00{agent}\x00{ts}\x00{vector_bytes_hex}\x00{source}
    """
    vec_hex = vector_after.to_bytes().hex()
    h_input = (
        f"v1\x00{prev_hash}\x00{sequence}\x00{agent_idx}\x00"
        f"{timestamp}\x00{vec_hex}\x00{source}"
    )
    return hashlib.sha256(h_input.encode("utf-8")).hexdigest()


# ─── Evolution Ledger ─────────────────────────────────────────────


class EvolutionLedger:
    """Append-only, hash-chained mutation log for UltramapSubstrate.

    Storage: JSONL file (one JSON object per line).
    Hash chain: SHA-256, null-byte separated, v1 scheme.
    Thread safety: single-writer assumed (substrate is single-process).

    Usage:
        ledger = EvolutionLedger("/path/to/evolution.jsonl")
        record = ledger.record_mutation(
            agent_idx=0,
            vector_before=ControlVector(10.0, 0.05, 0.1, 0.6),
            vector_after=ControlVector(12.0, 0.03, 0.08, 0.55),
            source="substrate",
        )
        # Replay and verify
        for record in ledger.replay():
            print(record.hash)
    """

    GENESIS_HASH = "GENESIS"

    def __init__(self, log_path: str | Path | None = None):
        if log_path is None:
            log_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "cortex-core", "evolution_ledger.jsonl",
            )
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory state
        self._sequence: int = 0
        self._head_hash: str = self.GENESIS_HASH
        self._record_count: int = 0

        # Recover state from existing log
        self._recover_head()

    def _recover_head(self) -> None:
        """Scan the last line of the log to recover sequence + head hash."""
        if not self._log_path.exists() or self._log_path.stat().st_size == 0:
            return

        last_line = ""
        try:
            with open(self._log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
                        self._record_count += 1
        except (OSError, IOError) as e:
            logger.error("Evolution ledger recovery failed: %s", e)
            return

        if last_line:
            try:
                payload = json.loads(last_line)
                self._sequence = payload["seq"]
                self._head_hash = payload["hash"]
            except (json.JSONDecodeError, KeyError) as e:
                logger.error("Evolution ledger corrupt tail: %s", e)

    @property
    def head_hash(self) -> str:
        return self._head_hash

    @property
    def sequence(self) -> int:
        return self._sequence

    @property
    def record_count(self) -> int:
        return self._record_count

    def record_mutation(
        self,
        agent_idx: int,
        vector_after: ControlVector,
        vector_before: ControlVector | None = None,
        performance_delta: float | None = None,
        source: str = "substrate",
        metadata: dict[str, Any] | None = None,
    ) -> MutationRecord:
        """Record a control vector mutation to the append-only ledger.

        Returns the MutationRecord with computed hash.
        """
        self._sequence += 1
        ts = time.time()

        new_hash = _compute_mutation_hash(
            prev_hash=self._head_hash,
            sequence=self._sequence,
            agent_idx=agent_idx,
            timestamp=ts,
            vector_after=vector_after,
            source=source,
        )

        record = MutationRecord(
            sequence=self._sequence,
            agent_idx=agent_idx,
            timestamp=ts,
            prev_hash=self._head_hash,
            hash=new_hash,
            vector_before=vector_before,
            vector_after=vector_after,
            performance_delta=performance_delta,
            source=source,
            metadata=metadata or {},
        )

        # Atomic append
        payload_line = _canonical_json(record.to_payload()) + "\n"
        try:
            with open(self._log_path, "a") as f:
                f.write(payload_line)
                f.flush()
                os.fsync(f.fileno())
        except (OSError, IOError) as e:
            self._sequence -= 1  # rollback sequence
            logger.error("Evolution ledger write failed: %s", e)
            raise

        self._head_hash = new_hash
        self._record_count += 1

        logger.debug(
            "EVO-LEDGER seq=%d agent=%d hash=%s…%s",
            self._sequence, agent_idx, new_hash[:8], new_hash[-4:]
        )
        return record

    def replay(self, verify: bool = True) -> Iterator[MutationRecord]:
        """Replay the entire ledger, optionally verifying hash chain integrity.

        Yields MutationRecord objects in chronological order.
        Raises ReplayVerificationError if chain is broken.
        """
        if not self._log_path.exists():
            return

        expected_prev = self.GENESIS_HASH
        expected_seq = 0

        with open(self._log_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    payload = json.loads(line)
                    record = MutationRecord.from_payload(payload)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    raise ReplayVerificationError(
                        f"Line {line_num}: corrupt record: {e}"
                    ) from e

                if verify:
                    expected_seq += 1
                    if record.sequence != expected_seq:
                        raise ReplayVerificationError(
                            f"Line {line_num}: sequence gap "
                            f"(expected {expected_seq}, got {record.sequence})"
                        )
                    if record.prev_hash != expected_prev:
                        raise ReplayVerificationError(
                            f"Line {line_num}: prev_hash mismatch "
                            f"(expected {expected_prev[:12]}…, got {record.prev_hash[:12]}…)"
                        )
                    recomputed = _compute_mutation_hash(
                        prev_hash=record.prev_hash,
                        sequence=record.sequence,
                        agent_idx=record.agent_idx,
                        timestamp=record.timestamp,
                        vector_after=record.vector_after,
                        source=record.source,
                    )
                    if recomputed != record.hash:
                        raise ReplayVerificationError(
                            f"Line {line_num}: hash mismatch "
                            f"(computed {recomputed[:12]}…, stored {record.hash[:12]}…)"
                        )
                    expected_prev = record.hash

                yield record

    def verify_integrity(self) -> dict[str, Any]:
        """Full chain verification. Returns audit report."""
        start = time.monotonic()
        count = 0
        errors: list[str] = []

        try:
            for record in self.replay(verify=True):
                count += 1
        except ReplayVerificationError as e:
            errors.append(str(e))

        elapsed = time.monotonic() - start
        return {
            "status": "VALID" if not errors else "CORRUPTED",
            "records_verified": count,
            "total_records": self._record_count,
            "errors": errors,
            "head_hash": self._head_hash,
            "elapsed_seconds": round(elapsed, 4),
        }

    def get_agent_history(self, agent_idx: int) -> list[MutationRecord]:
        """Extract mutation history for a specific agent."""
        return [r for r in self.replay(verify=False) if r.agent_idx == agent_idx]

    def get_performance_trajectory(self) -> list[dict[str, Any]]:
        """Extract performance delta timeline for trend analysis."""
        trajectory = []
        for record in self.replay(verify=False):
            if record.performance_delta is not None:
                trajectory.append({
                    "seq": record.sequence,
                    "ts": record.timestamp,
                    "agent_idx": record.agent_idx,
                    "perf_delta": record.performance_delta,
                    "vector_magnitude": record.vector_after.magnitude(),
                })
        return trajectory

    def compact_to_checkpoint(self) -> dict[str, Any]:
        """Generate a checkpoint summary without modifying the log.
        
        Returns a snapshot that can be used to validate future replays
        without re-reading the entire log.
        """
        from cortex.ledger.merkle import MerkleTree

        hashes: list[str] = []
        for record in self.replay(verify=True):
            hashes.append(record.hash)

        tree = MerkleTree(hashes) if hashes else None
        return {
            "sequence": self._sequence,
            "record_count": self._record_count,
            "head_hash": self._head_hash,
            "merkle_root": tree.root_hash if tree else None,
            "timestamp": time.time(),
        }
