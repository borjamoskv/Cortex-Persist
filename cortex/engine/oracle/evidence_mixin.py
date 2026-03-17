"""Evidence Chain Verification for Forgetting Oracle."""

from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.services.trust import TrustService

logger = logging.getLogger("cortex.oracle.evidence")


class EvidenceMixin:
    """Verifies evidence chain internal consistency (Ω₃)."""

    _trust: Optional[TrustService]

    def _verify_evidence_chain(self, records: list[dict[str, Any]]) -> tuple[bool, str]:
        """Verify ledger evidence chain internal consistency (Ω₃)."""
        if not records:
            return True, "NO_RECORDS"

        if self._trust:
            # Use real TrustService for full cryptographic verification
            for record in records:
                fact_id = record.get("tx_id")  # Assuming tx_id maps to something trust can verify
                if fact_id:
                    # TrustService returns FactVerification (frozen dataclass)
                    res = self._trust.verify_fact_chain(fact_id)
                    if not res.valid:
                        return False, f"TRUST_FAILURE:{fact_id}"

        trails = []
        for record in records:
            audit = record.get("detail", {}).get("audit_trail")
            if audit and "prev_proof" in audit and "current_proof" in audit:
                trails.append(audit)

        if not trails:
            return True, "NO_CHAIN"

        # Verificar encadenamiento
        for i in range(1, len(trails)):
            if trails[i]["prev_proof"] != trails[i - 1]["current_proof"]:
                logger.error(
                    "❌ [ORACLE] Evidence chain broken at eviction %d → %d",
                    trails[i - 1].get("eviction_id", "?"),
                    trails[i].get("eviction_id", "?"),
                )
                return False, trails[i]["prev_proof"]

        return True, trails[-1]["current_proof"]
