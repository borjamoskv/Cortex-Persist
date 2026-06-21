"""
AI Code Governance Gateway.

Enterprise control plane for LLM-driven code changes. Acts as a gatekeeper
for CI/CD pipelines, scoring risk/entropy and cryptographically signing approvals.
"""

import logging
from dataclasses import dataclass
from typing import Any

from cortex.engine.chronos_roi import CHRONOS, ChronosReport
from cortex.guards.enterprise_guard import EnterpriseRBACGuard

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.auth.enterprise_identity import SovereignIdentity

logger = logging.getLogger("cortex.gateway.code_governance")

@dataclass
class RiskProfile:
    entropy_score: float
    risk_level: str
    reasons: list[str]
    approved: bool

class CodeGovernanceGateway:
    """
    Evaluates, scores, and governs code mutations (PRs) before they are merged.
    """

    def __init__(self, ledger: EnterpriseAuditLedger, rbac_guard: EnterpriseRBACGuard):
        self.ledger = ledger
        self.rbac_guard = rbac_guard
        # Thresholds
        self.max_entropy_threshold = 0.75

    def _calculate_risk(self, pr_payload: dict[str, Any]) -> RiskProfile:
        """
        Calculates the thermodynamic entropy (risk) of a PR.
        This is a deterministic proxy for 'semantic drift' and 'blast radius'.
        """
        files_changed = pr_payload.get("files_changed", 0)
        lines_added = pr_payload.get("additions", 0)
        lines_deleted = pr_payload.get("deletions", 0)
        has_tests = pr_payload.get("includes_tests", False)

        entropy = 0.0
        reasons = []

        # High churn = high entropy
        if lines_added + lines_deleted > 1000:
            entropy += 0.4
            reasons.append("Massive diff size (>1000 lines).")

        if files_changed > 15:
            entropy += 0.3
            reasons.append("High blast radius (>15 files touched).")

        if not has_tests:
            entropy += 0.3
            reasons.append("Missing test coverage for mutation.")

        # Baseline risk
        entropy = min(1.0, entropy + 0.1)
        
        approved = entropy < self.max_entropy_threshold
        level = "CRITICAL" if entropy >= 0.8 else "HIGH" if entropy >= 0.5 else "MEDIUM" if entropy >= 0.2 else "LOW"

        return RiskProfile(entropy_score=round(entropy, 2), risk_level=level, reasons=reasons, approved=approved)

    async def evaluate_pull_request(self, identity: SovereignIdentity, pr_id: str, pr_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Entrypoint for CI/CD pipelines (e.g., GitHub Actions).
        1. Validates Identity (RBAC).
        2. Scores the risk.
        3. Issues Cryptographic Seal on Approval.
        4. Calculates ROI.
        """
        # 1. BFT Identity Verification
        self.rbac_guard.validate_proposal(identity, action="gateway:evaluate_pr", resource=f"pr:{pr_id}", payload=pr_payload)

        # 2. Evaluate Risk
        risk_profile = self._calculate_risk(pr_payload)
        
        status = "APPROVED" if risk_profile.approved else "REJECTED"
        
        # 3. Cryptographic Ledger Audit
        audit_id = await self.ledger.log_action(
            tenant_id=identity.tenant_id,
            actor_role=identity.role,
            actor_id=identity.actor_id,
            action="PR_GOVERNANCE_AUDIT",
            resource=f"pr:{pr_id}:entropy={risk_profile.entropy_score}",
            status=status
        )

        # 4. CHRONOS ROI (How much money did we save by doing this autonomously?)
        # A human would spend 15 mins base + 2 mins per file changed for a manual security audit.
        hours_saved = CHRONOS.calculate_hours_saved(
            commits=pr_payload.get("commits", 1),
            lines_added=pr_payload.get("additions", 0),
            lines_deleted=pr_payload.get("deletions", 0)
        )
        money_saved = round(hours_saved * CHRONOS.hourly_rate, 2)
        
        roi_report = ChronosReport(
            file_count=pr_payload.get("files_changed", 0),
            git_commits=pr_payload.get("commits", 1),
            git_added=pr_payload.get("additions", 0),
            git_deleted=pr_payload.get("deletions", 0),
            hours_saved=hours_saved,
            money_saved=money_saved,
            roi_ratio=999.0, # Infinite ROI for purely autonomous operations (cost=0)
            cost=0.0
        )

        return {
            "pr_id": pr_id,
            "status": status,
            "audit_proof": audit_id,
            "risk_profile": {
                "score": risk_profile.entropy_score,
                "level": risk_profile.risk_level,
                "reasons": risk_profile.reasons
            },
            "roi_receipt": roi_report.to_dict()
        }
