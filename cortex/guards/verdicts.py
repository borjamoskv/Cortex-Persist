import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum


class GuardViolationError(Exception):
    """Raised when an agent action violates a P0 Critical Policy."""

    def __init__(self, message: str, verdict_report: "VerdictReport"):
        super().__init__(message)
        self.verdict_report = verdict_report


class PolicyVerdict(str, Enum):
    CORTEX_PASS = "CORTEX_PASS"
    CORTEX_WARN = "CORTEX_WARN"
    CORTEX_BLOCK = "CORTEX_BLOCK"
    CORTEX_ROLLBACK_READY = "CORTEX_ROLLBACK_READY"


@dataclass
class VerdictReport:
    verdict: PolicyVerdict
    rule_id: str | None = None
    description: str | None = None
    severity: str | None = None
    timestamp: float = field(default_factory=time.time)
    signatures: list[str] = field(default_factory=list)
    quorum_reached: bool = False

    @property
    def hash(self) -> str:
        """Returns the SHA3-256 hash of the verdict report (CORTEX Determinism)"""
        signatures_str = ",".join(sorted(self.signatures))
        content = (
            f"{self.verdict.value}:{self.rule_id}:{self.severity}:{self.timestamp}:{signatures_str}"
        )
        return hashlib.sha3_256(content.encode("utf-8")).hexdigest()
