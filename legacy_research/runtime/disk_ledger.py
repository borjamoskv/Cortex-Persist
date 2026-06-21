# [C5-REAL] Exergy-Maximized
import json
import os
from typing import Any


class DiskLedger:
    """Immutable persistent append-only causality log."""

    def __init__(self, filepath: str = "ledger.jsonl"):
        self.filepath = filepath

    def append(self, event: dict[str, Any]):
        with open(self.filepath, "a") as f:
            f.write(json.dumps(event) + "\n")

    def query_from(self, version: int) -> list[dict[str, Any]]:
        if not os.path.exists(self.filepath):
            return []
        events = []
        with open(self.filepath) as f:
            for idx, line in enumerate(f):
                if idx >= version:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Ledger corruption handling
                        break
        return events
