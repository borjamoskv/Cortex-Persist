# [C5-REAL] Exergy-Maximized
"""
Merkle Checkpoint Indexing and Verification Flow.

This module provides an indexing mechanism for the Evolution Ledger. By
chunking the append-only log into blocks (e.g., every 1000 records) and
computing a Merkle Root for each block, we enable:
1. Parallel verification of ledger chunks.
2. Fast-forwarding state without full replay verification.
3. Cryptographic proofs of inclusion for individual mutations (O(log N)).
"""

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from cortex.engine.core.evolution_ledger import EvolutionLedger, ReplayMode
from cortex.ledger.merkle import MerkleTree

logger = logging.getLogger("cortex.checkpoint")


@dataclass
class Checkpoint:
    sequence_start: int
    sequence_end: int
    record_count: int
    merkle_root: str
    head_hash: str
    timestamp: float

    def to_payload(self) -> dict[str, Any]:
        return {
            "seq_start": self.sequence_start,
            "seq_end": self.sequence_end,
            "count": self.record_count,
            "root": self.merkle_root,
            "head": self.head_hash,
            "ts": self.timestamp,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Checkpoint":
        return cls(
            sequence_start=payload["seq_start"],
            sequence_end=payload["seq_end"],
            record_count=payload["count"],
            merkle_root=payload["root"],
            head_hash=payload["head"],
            timestamp=payload["ts"],
        )


class CheckpointManager:
    """Manages Merkle checkpoints for an EvolutionLedger."""

    def __init__(self, ledger: EvolutionLedger, chunk_size: int = 1000):
        self.ledger = ledger
        self.chunk_size = chunk_size
        self._index_path = ledger._log_path.with_suffix(".checkpoints.jsonl")

    def generate_index(self, force_rebuild: bool = False) -> None:
        """Scan the ledger and build missing checkpoints."""
        start_seq = 0
        if not force_rebuild and self._index_path.exists():
            # Find the last checkpoint
            last_cp = self.get_latest_checkpoint()
            if last_cp:
                start_seq = last_cp.sequence_end

        mode = "w" if force_rebuild else "a"

        current_chunk_hashes = []
        chunk_start_seq = start_seq + 1
        last_hash = EvolutionLedger.GENESIS_HASH

        try:
            with open(self._index_path, mode) as out_f:
                for record in self.ledger.replay(mode=ReplayMode.BEST_EFFORT):
                    if record.sequence <= start_seq:
                        continue

                    current_chunk_hashes.append(record.hash)
                    last_hash = record.hash

                    if len(current_chunk_hashes) == self.chunk_size:
                        tree = MerkleTree(current_chunk_hashes)
                        cp = Checkpoint(
                            sequence_start=chunk_start_seq,
                            sequence_end=record.sequence,
                            record_count=self.chunk_size,
                            merkle_root=tree.root_hash,
                            head_hash=last_hash,
                            timestamp=record.timestamp,
                        )
                        out_f.write(json.dumps(cp.to_payload()) + "\n")
                        out_f.flush()

                        current_chunk_hashes = []
                        chunk_start_seq = record.sequence + 1

                # Write remaining if any (incomplete chunk)
                if current_chunk_hashes:
                    tree = MerkleTree(current_chunk_hashes)
                    cp = Checkpoint(
                        sequence_start=chunk_start_seq,
                        sequence_end=record.sequence,
                        record_count=len(current_chunk_hashes),
                        merkle_root=tree.root_hash,
                        head_hash=last_hash,
                        timestamp=record.timestamp,
                    )
                    out_f.write(json.dumps(cp.to_payload()) + "\n")
                    out_f.flush()

        except Exception as e:
            logger.error(f"Failed to generate index: {e}")

    def iter_checkpoints(self) -> Iterator[Checkpoint]:
        """Iterate over all stored checkpoints."""
        if not self._index_path.exists():
            return

        with open(self._index_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    yield Checkpoint.from_payload(json.loads(line))

    def get_latest_checkpoint(self) -> Checkpoint | None:
        """Get the most recent checkpoint."""
        last_cp = None
        for cp in self.iter_checkpoints():
            last_cp = cp
        return last_cp

    def verify_ledger_with_checkpoints(self) -> dict[str, Any]:
        """Verify the ledger using the chunked Merkle roots.

        This enables validating blocks independently. For a full check,
        it still reads the records, but groups them by checkpoint.
        """
        import time

        start = time.monotonic()

        checkpoints = list(self.iter_checkpoints())
        if not checkpoints:
            return {"status": "NO_INDEX", "verified_chunks": 0}

        cp_idx = 0
        current_cp = checkpoints[cp_idx]
        current_chunk_hashes = []

        errors = []
        records_read = 0

        # We assume the user wants full read to verify hashes match the roots
        for record in self.ledger.replay(mode=ReplayMode.STRICT):
            records_read += 1
            if record.sequence < current_cp.sequence_start:
                continue

            current_chunk_hashes.append(record.hash)

            if record.sequence == current_cp.sequence_end:
                # Verify chunk Merkle Root
                tree = MerkleTree(current_chunk_hashes)
                if tree.root_hash != current_cp.merkle_root:
                    errors.append(
                        f"Merkle Root mismatch at chunk {current_cp.sequence_start}-{current_cp.sequence_end}"
                    )

                cp_idx += 1
                if cp_idx < len(checkpoints):
                    current_cp = checkpoints[cp_idx]
                    current_chunk_hashes = []
                else:
                    break

        elapsed = time.monotonic() - start

        return {
            "status": "VALID" if not errors else "CORRUPTED",
            "verified_chunks": len(checkpoints),
            "records_read": records_read,
            "errors": errors,
            "elapsed_seconds": round(elapsed, 4),
        }
