# [C5-REAL] Exergy-Maximized
"""L3 Cold Storage Engine - Weaponized Forgetting (Apoptosis).

Writes dead/pruned facts into an immutable, compressed Parquet block sequence.
Extracts thermodynamic waste from the active SQLite WAL, archiving it
for offline adversarial training or forensic audits.

Uses pyarrow to append rows to a partitioned Parquet dataset without loading
the whole table into memory.
"""

import logging
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False

logger = logging.getLogger("cortex.engine.l3_archive")

class L3ArchiveEngine:
    """C5-REAL: L3 Cold Storage for Epistemic Pruning."""

    def __init__(self, archive_dir: str | Path | None = None):
        if not archive_dir:
            # Default to an archive folder next to the cortex db
            db_path = os.environ.get("CORTEX_DB_PATH", os.path.expanduser("~/.cortex/cortex.db"))
            self.archive_dir = Path(db_path).parent / "l3_archive"
        else:
            self.archive_dir = Path(archive_dir)

        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        if not PYARROW_AVAILABLE:
            logger.warning("[L3-ARCHIVE] PyArrow not installed. L3 Archiving will be degraded (No-op).")

    def archive_facts(self, facts: list[Mapping[str, Any]]) -> bool:
        """
        Compresses and flushes a batch of dead facts into Parquet L3 storage.
        
        Args:
            facts: List of dictionaries representing the purged facts.
            
        Returns:
            True if archived successfully, False otherwise.
        """
        if not facts:
            return True

        if not PYARROW_AVAILABLE:
            return False

        try:
            # We partition by year-month to avoid giant monolithic files
            now = datetime.now(timezone.utc)
            partition_key = now.strftime("%Y-%m")
            
            # Normalize schema dynamically based on the first fact
            # (Assuming homogenous batch)
            sanitized_facts = []
            for f in facts:
                # Convert complex types (lists/dicts) to JSON strings for cold storage
                # to prevent pyarrow schema conflicts
                row = {}
                for k, v in f.items():
                    if isinstance(v, (list, dict)):
                        import json
                        row[k] = json.dumps(v)
                    elif v is None:
                        row[k] = ""
                    else:
                        row[k] = str(v)
                # Inject apoptosis metadata
                row["_apoptosis_ts"] = now.isoformat()
                sanitized_facts.append(row)

            table = pa.Table.from_pylist(sanitized_facts)
            
            # Path: l3_archive/facts_2026-06.parquet
            file_path = self.archive_dir / f"facts_{partition_key}.parquet"
            
            if file_path.exists():
                # Append by writing to a new file in a dataset if using partitions, 
                # or read+concat+write if direct file.
                # To maintain O(1) appending, we could write multiple files,
                # but for simplicity, we append via reading and rewriting or just 
                # writing a new batch file if we treat the dir as a dataset.
                # For C5-REAL Exergy efficiency: we write sequentially numbered chunks.
                chunk_id = int(now.timestamp() * 1000)
                file_path = self.archive_dir / f"facts_{partition_key}_{chunk_id}.parquet"

            pq.write_table(table, file_path, compression="snappy")
            logger.info("Weaponized Forgetting: %d facts archived to L3 (%s)", len(facts), file_path.name)
            return True

        except Exception as e:
            logger.error("L3 Archival failure: %s", e)
            return False

l3_archiver = L3ArchiveEngine()
