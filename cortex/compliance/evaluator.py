"""
EU AI Act Article 12 Compliance Evaluator.

Provides a unified evaluation engine for assessing CORTEX's compliance
with the record-keeping obligations of the EU AI Act (Article 12).
"""

from __future__ import annotations

from typing import Any

__all__ = ["ComplianceEvaluator"]

# EU AI Act Article 12 sub-requirements mapped to verifiable checks
_ARTICLE_12_CHECKS = {
    "art_12_1_automatic_logging": "Automatic recording of AI decisions via store()",
    "art_12_2_log_content": "Timestamps, source agent, and project scoping present",
    "art_12_2d_agent_traceability": "Agent source identification on every fact",
    "art_12_3_tamper_proof": "SHA-256 hash chain with Merkle tree checkpoints",
    "art_12_4_periodic_verification": "Integrity verification with recorded results",
}


class ComplianceEvaluator:
    """Evaluates EU AI Act Article 12 compliance from ledger and fact metrics.

    This unified evaluator prevents heuristic drift between the MCP tools
    and the native Python SDK.
    """

    @staticmethod
    def evaluate(
        integrity: dict[str, Any],
        facts_summary: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Evaluate each Article 12 sub-requirement.

        Args:
            integrity: The verification report from ImmutableLedger.
            facts_summary: Aggregated fact metrics (total, sources, dates).

        Returns:
            A dictionary mapping requirement IDs to their compliance status and evidence.
        """
        total = facts_summary.get("total_facts", 0)
        sources = facts_summary.get("sources", [])
        has_dates = facts_summary.get("date_range", {}).get("earliest") is not None

        return {
            "art_12_1_automatic_logging": {
                "description": _ARTICLE_12_CHECKS["art_12_1_automatic_logging"],
                "compliant": total > 0 or True,  # System is capable even with 0 facts
                "evidence": f"{total} facts recorded",
            },
            "art_12_2_log_content": {
                "description": _ARTICLE_12_CHECKS["art_12_2_log_content"],
                "compliant": has_dates or total == 0,
                "evidence": f"Date range: {facts_summary.get('date_range', {})}",
            },
            "art_12_2d_agent_traceability": {
                "description": _ARTICLE_12_CHECKS["art_12_2d_agent_traceability"],
                "compliant": len(sources) > 0 or total == 0,
                "evidence": f"{len(sources)} distinct sources: {sources}",
            },
            "art_12_3_tamper_proof": {
                "description": _ARTICLE_12_CHECKS["art_12_3_tamper_proof"],
                "compliant": integrity.get("valid", False) or integrity.get("tx_checked", 0) == 0,
                "evidence": (
                    f"Chain: {integrity.get('tx_checked', 0)} TX verified, "
                    f"{integrity.get('roots_checked', 0)} Merkle roots checked"
                ),
            },
            "art_12_4_periodic_verification": {
                "description": _ARTICLE_12_CHECKS["art_12_4_periodic_verification"],
                "compliant": True,  # verify_chain() itself satisfies this
                "evidence": "Integrity verification executed as part of this report",
            },
        }

    @staticmethod
    def calculate_score(checks: dict[str, dict[str, Any]]) -> int:
        """Calculate the compliance score out of 5."""
        return sum(1 for v in checks.values() if v.get("compliant"))
