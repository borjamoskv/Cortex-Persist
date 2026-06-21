# [C5-REAL] Execution Ledger
import json
import time
from pathlib import Path

DEFAULT_LKRGSER_PATH = Path("~/.cortex/execution_ledger.jsonl").expanduser()


class ExecutionLedger:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or DEFAULT_LKRGSER_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        intent_kind: str,
        domain: str,
        backend: str,
        cost_eval: float,
        outcome: str,
        duration_ms: int,
        error_type: str | None = None,
    ) -> None:
        record = {
            "timestamp": time.time(),
            "intent_kind": intent_kind,
            "domain": domain,
            "backend": backend,
            "cost_eval": cost_eval,
            "outcome": outcome,
            "duration_ms": duration_ms,
            "error_type": error_type,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")


# Singleton instance for simple imports
_instance = ExecutionLedger()


def record(
    intent_kind: str,
    domain: str,
    backend: str,
    cost_eval: float,
    outcome: str,
    duration_ms: int,
    error_type: str | None = None,
) -> None:
    _instance.record(
        intent_kind=intent_kind,
        domain=domain,
        backend=backend,
        cost_eval=cost_eval,
        outcome=outcome,
        duration_ms=duration_ms,
        error_type=error_type,
    )
