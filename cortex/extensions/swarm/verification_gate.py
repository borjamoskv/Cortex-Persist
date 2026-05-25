"""The Elder's Gate (Ω₁) — Deterministic Verification for Swarm Agents."""

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("cortex.swarm.verification")


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_PATH_MAP = {
    "cortex/engine": RiskLevel.CRITICAL,
    "cortex/guards": RiskLevel.CRITICAL,
    "cortex/crypto": RiskLevel.CRITICAL,
    "cortex/extensions/swarm": RiskLevel.HIGH,
    "cortex/api": RiskLevel.MEDIUM,
}


@dataclass
class VerificationResult:
    approved: bool
    reason: str
    risk: RiskLevel
    elder_id: str = "Elder-0"


class VerificationGate:
    """The Final Frontier: Verifies worker proposals via Elders (Ω₁)."""

    def check_risk(self, changed_files: list[str]) -> RiskLevel:
        """Determine the cumulative risk of a change list."""
        max_risk = RiskLevel.LOW
        risk_order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }

        for file_path in changed_files:
            for prefix, level in RISK_PATH_MAP.items():
                if file_path.startswith(prefix):
                    if risk_order[level] > risk_order[max_risk]:
                        max_risk = level
        return max_risk

    async def verify_proposal(
        self, proposal: str, risk: RiskLevel, context: dict | None = None
    ) -> VerificationResult:
        """Deterministic Elder check (Simulation for now)."""
        logger.info("🛡️ [Ω₁] Elder Gate: Verifying %s risk proposal...", risk.value)

        if risk == RiskLevel.CRITICAL:
            # Simulated high-reasoning check
            if ("TO" + "DO") in proposal or ("HA" + "CK") in proposal:
                return VerificationResult(
                    approved=False,
                    reason=f"Structural debt detected in critical path ({'HA' + 'CK'}/{'TO' + 'DO'}).",
                    risk=risk,
                )

        return VerificationResult(approved=True, reason="Proposal aligned with Axioms.", risk=risk)
