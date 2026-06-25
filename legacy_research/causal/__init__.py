# [C5-REAL] Exergy-Maximized
"""Causal engine module.

Enforces taint checks, anomalies tracking, and verification within CORTEX.
"""

from __future__ import annotations

from legacy_research.engine.causal.anomaly_bridge import AnomalyBridge
from legacy_research.engine.causal.taint_engine import (
    C5NativeSocketIngestor,
    MHCAntigenRouter,
    TaintValidationError,
    canonicalize_content,
    enforce_taint_check,
    generate_secure_taint_token,
    verify_taint_token,
)
from legacy_research.engine.causal.verification_oracle import (
    InvariantViolationError,
    verify_approved_auth_signatures,
    verify_c5_state_machine,
    verify_causal_dag,
    verify_ledger_continuity,
    verify_nonce_uniqueness,
)

__all__ = [
    "canonicalize_content",
    "generate_secure_taint_token",
    "verify_taint_token",
    "enforce_taint_check",
    "TaintValidationError",
    "C5NativeSocketIngestor",
    "MHCAntigenRouter",
    "AnomalyBridge",
    "verify_c5_state_machine",
    "InvariantViolationError",
    "verify_ledger_continuity",
    "verify_causal_dag",
    "verify_approved_auth_signatures",
    "verify_nonce_uniqueness",
]
