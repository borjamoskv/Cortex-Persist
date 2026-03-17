"""
SORTU-Ω Exceptions & Error Codes

This module defines the trust-aware error hierarchy for the SORTU-Ω SDK.
Strict separation is maintained between Rejections (governance) and
Failures (operational), as defined in ERROR-CODE-REGISTRY.md.
"""

from typing import Literal


class CortexError(Exception):
    """Base error for all CORTEX client exceptions."""

    def __init__(self, status_code: int, detail: str, code: str):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(f"[{code}] {status_code}: {detail}")


class RejectionError(CortexError):
    """
    Raised when an operation is rejected due to policy, safety, consistency,
    integrity, or compliance violations. Rejections are deterministic and
    should not be indiscriminately retried without modifying the input.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str,
        category: Literal["policy", "safety", "consistency", "integrity", "compliance"],
        severity: Literal["low", "medium", "high", "critical"],
        layer: Literal["admission", "guards", "schema", "ledger", "output"],
        mitigation: str | None = None,
    ):
        super().__init__(status_code, detail, code)
        self.category = category
        self.severity = severity
        self.layer = layer
        self.mitigation = mitigation


class FailureError(CortexError):
    """
    Raised when an operation fails due to operational issues (dependency unavailability,
    storage exhaustion, runtime timeouts). Failures may be transient and retryable.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str,
        category: Literal["dependency", "storage", "runtime", "capability"],
        is_retryable: bool,
        retry_after_ms: int | None = None,
    ):
        super().__init__(status_code, detail, code)
        self.category = category
        self.is_retryable = is_retryable
        self.retry_after_ms = retry_after_ms


# ─── Error Code Registry Constants ─────────────────────────────────────

# Rejection Codes - Consistency
ERR_CONTRADICTION = "ERR_REJ_CONSISTENCY_001"
ERR_ORPHAN_EDGE = "ERR_REJ_CONSISTENCY_002"

# Rejection Codes - Integrity
ERR_SIGNATURE_INVALID = "ERR_REJ_INTEGRITY_001"
ERR_CHAIN_BROKEN = "ERR_REJ_INTEGRITY_002"

# Rejection Codes - Safety
ERR_TAINT_TOO_HIGH = "ERR_REJ_SAFETY_001"
ERR_PII_DETECTED = "ERR_REJ_SAFETY_002"

# Rejection Codes - Policy
ERR_TENANT_ISOLATION = "ERR_REJ_POLICY_001"
ERR_EVIDENCE_INSUFFICIENT = "ERR_REJ_POLICY_002"

# Rejection Codes - Compliance
ERR_AUDIT_LOG_FULL = "ERR_REJ_COMPLIANCE_001"

# Failure Codes - Dependency
ERR_EMBEDDER_UNAVAILABLE = "ERR_FAIL_DEP_001"
ERR_LLM_TIMEOUT = "ERR_FAIL_DEP_002"

# Failure Codes - Storage
ERR_DISK_EXHAUSTED = "ERR_FAIL_STORE_001"
ERR_LOCK_CONTENTION = "ERR_FAIL_STORE_002"

# Failure Codes - Runtime
ERR_QUERY_TIMEOUT = "ERR_FAIL_RUNTIME_001"
ERR_OOM_PROTECTION = "ERR_FAIL_RUNTIME_002"

# Failure Codes - Capability
ERR_CAPABILITY_LOCKED = "ERR_FAIL_CAP_001"
