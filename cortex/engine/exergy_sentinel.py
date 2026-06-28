# [C5-REAL] Exergy-Maximized
"""
Exergy Sentinel: Enforces the cryptographic Proof YAML block structure (Claim/Proof/Confidence) 
on all structural generative assertions before they cross the Byzantine Boundary.
"""
import re
import logging
from cortex.guards.landauer_guard import LandauerGuard
from cortex.security.types import GuardViolation

logger = logging.getLogger("cortex.engine.exergy_sentinel")

class ExergySentinel:
    """Intercepts generative output and forces strict YAML structural assertions (L1/Φ2)."""
    
    YAML_PROOF_REGEX = re.compile(
        r"```yaml\s*\nClaim:\s*(.*?)\nProof:\s*\{\s*Base:\s*(.*?),\s*Range:\s*\[(.*?)\],\s*Confidence:\s*(C[1-5])\s*\}\s*\n```",
        re.MULTILINE | re.IGNORECASE
    )

    @classmethod
    def enforce_yaml_structure(cls, content: str) -> dict:
        """
        Validates that the content contains a properly formatted C5-REAL YAML claim.
        Returns the parsed dictionary if valid, raises GuardViolation otherwise.
        """
        match = cls.YAML_PROOF_REGEX.search(content)
        if not match:
            logger.error("Exergy Sentinel: No YAML Proof block found. Anergy detected.")
            raise GuardViolation(
                "Anergy Detected: Generative output lacks the mandatory YAML Claim/Proof block."
            )
        
        claim, base, range_val, confidence = match.groups()
        
        # Verify Shannon Entropy on the Claim using LandauerGuard
        if not LandauerGuard.validate(claim):
            raise GuardViolation(
                f"Exergy Sentinel: Claim '{claim}' fails Thermodynamic Compression (Landauer Ω₄)."
            )

        if confidence != "C5":
            logger.warning(f"Exergy Sentinel: Sub-optimal confidence level detected ({confidence}).")

        return {
            "claim": claim.strip(),
            "base": base.strip(),
            "range": range_val.strip(),
            "confidence": confidence.strip()
        }

    @classmethod
    def intercept(cls, content: str) -> str:
        """
        Main interception point for the Write-Path.
        Returns the content if valid, otherwise raises an exception.
        """
        cls.enforce_yaml_structure(content)
        return content
