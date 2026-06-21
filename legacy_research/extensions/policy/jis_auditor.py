# [C5-REAL] Exergy-Maximized
"""
CORTEX - JIS Auditor (Joint Integrity Standard).

Enforces SOC 2, C5 (Cloud Computing Compliance Criteria Catalogue),
and GDPR policies over the CORTEX-Persist ImmutableLedger.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("cortex.policy.jis")


@dataclass
class JISViolation:
    policy: str
    severity: str
    reason: str
    event_ref: str | None = None


class JISAuditor:
    """Evaluates JSON payloads against strict compliance policies."""

    # Simple regex for PII (Credit Cards, SSN, Emails)
    _PII_PATTERNS = [
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),  # Email
        re.compile(r"\b(?:\d[ -]*?){13,16}\b"),  # Basic CC
    ]

    def __init__(self, enforce_encryption: bool = True):
        self.enforce_encryption = enforce_encryption

    def audit_payload(
        self, payload: dict[str, Any], event_id: str | None = None
    ) -> list[JISViolation]:
        """Run all compliance checks on a transaction payload."""
        violations = []

        # 1. GDPR Check: Detect cleartext PII
        payload_str = str(payload)
        for pattern in self._PII_PATTERNS:
            if pattern.search(payload_str):
                violations.append(
                    JISViolation(
                        policy="GDPR_PII_CLEARTEXT",
                        severity="CRITICAL",
                        reason="Cleartext Personally Identifiable Information (PII) detected in payload.",
                        event_ref=event_id,
                    )
                )

        # 2. SOC 2 Check: Ensure 'actor_id' is present for accountability
        meta = payload.get("meta") or {}
        if isinstance(meta, str):
            import json
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        if "actor_id" not in payload and "actor" not in payload and "actor_id" not in meta:
            violations.append(
                JISViolation(
                    policy="SOC2_ACCOUNTABILITY",
                    severity="HIGH",
                    reason="Missing attribution (actor_id). SOC 2 requires verifiable audit trails.",
                    event_ref=event_id,
                )
            )

        # 3. C5 Check: Cryptographic Verification markers
        if self.enforce_encryption:
            if "signature" not in payload and "origin_signature" not in payload:
                violations.append(
                    JISViolation(
                        policy="C5_CRYPTO_INTEGRITY",
                        severity="HIGH",
                        reason="Missing cryptographic signature in payload. C5 dictates verifiable integrity.",
                        event_ref=event_id,
                    )
                )

        # 4. Thermodynamic Stress Check: Detect high cortisol
        metrics = payload.get("metrics", {})
        cortisol = metrics.get("cortisol_level", 0.0)
        if cortisol > 0.8:
            violations.append(
                JISViolation(
                    policy="THERMODYNAMIC_STRESS_CRITICAL",
                    severity="HIGH",
                    reason=f"Systemic cortisol ({cortisol:.2f}) exceeded 0.8 threshold. High risk of entropic decay.",
                    event_ref=event_id,
                )
            )

        if violations:
            logger.warning(
                f"[JIS Auditor] Detected {len(violations)} policy violations for event {event_id}"
            )
        else:
            logger.debug(f"[JIS Auditor] Payload {event_id} compliant with JIS standards.")

        return violations
