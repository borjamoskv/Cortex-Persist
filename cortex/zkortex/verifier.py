"""
ZKORTEX — Public Verifier.

El Verifier es la entidad externa: auditores, clientes, reguladores.
Opera SOLO con datos públicos (roots, commitments, proofs).
NUNCA ve los secretos internos de CORTEX.

Principio soberano: El Verifier puede CONFIAR en CORTEX
                    sin que CORTEX tenga que EXPONER nada.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from cortex.zkortex.commitment import KnowledgeCommitment
from cortex.zkortex.merkle import ZKMembershipProof
from cortex.zkortex.range_proof import ZKRangeProof, verify_range_proof

logger = logging.getLogger("cortex.zkortex.verifier")


@dataclass(frozen=True)
class VerificationResult:
    """Resultado de una verificación ZK."""

    is_valid: bool
    proof_type: str
    verified_at: float
    details: str
    public_root: str | None = None


class ZKOrtexVerifier:
    """
    Verificador público para los Zero-Knowledge Proofs de CORTEX.

    El Verifier:
      ✓ Verifica membership proofs con solo el root público
      ✓ Verifica range proofs con solo los parámetros del rango
      ✓ Verifica commitments si el Prover decide abrir (revealing)
      ✗ NUNCA recibe los hechos originales
      ✗ NUNCA puede inferir el contenido del knowledge set

    El Verifier puede ser ejecutado por terceros sin ningún acceso a CORTEX.
    """

    def __init__(self, expected_root: str | None = None) -> None:
        """
        Args:
            expected_root: El Merkle Root publicado por CORTEX.
                           Si se provee, toda prueba de membresía se valida
                           contra este root (pin de confianza).
        """
        self._expected_root = expected_root
        logger.info("ZKOrtexVerifier initialized. Root pin: %s", expected_root)

    def verify_membership(
        self,
        proof: ZKMembershipProof,
        element_to_verify: str,
    ) -> VerificationResult:
        """
        Verifica que `element_to_verify` pertenece al conjunto de CORTEX.

        Requires: El Prover debe haber compartido el elemento (no el conjunto).
        Esto es la "apertura selectiva": CORTEX elige con qué elementos
        revelar membresía.

        Args:
            proof: La ZKMembershipProof generada por el Prover.
            element_to_verify: El elemento cuya membresía se verifica.
        """
        # Si tenemos un root pinned, verifica que el proof usa el mismo root
        if self._expected_root and proof.root != self._expected_root:
            return VerificationResult(
                is_valid=False,
                proof_type="membership",
                verified_at=time.time(),
                details=f"Root mismatch. Expected: {self._expected_root[:16]}... "
                f"Got: {proof.root[:16]}...",
                public_root=proof.root,
            )

        try:
            is_valid = proof.verify(element_to_verify)
        except (ValueError, IndexError) as e:
            return VerificationResult(
                is_valid=False,
                proof_type="membership",
                verified_at=time.time(),
                details=f"Proof verification error: {e}",
                public_root=proof.root,
            )

        logger.info(
            "Membership verification: %s. Root: %s",
            "VALID" if is_valid else "INVALID",
            proof.root[:16] + "...",
        )
        return VerificationResult(
            is_valid=is_valid,
            proof_type="membership",
            verified_at=time.time(),
            details="Proof valid — element is a member of the sovereign knowledge set."
            if is_valid
            else "Proof INVALID — element not in set or tampered proof.",
            public_root=proof.root,
        )

    def verify_range(self, proof: ZKRangeProof) -> VerificationResult:
        """
        Verifica que el valor secreto de CORTEX cae en [proof.min_val, proof.max_val].
        No requiere conocer el valor exacto.
        """
        is_valid = verify_range_proof(proof)
        logger.info(
            "Range verification [%d, %d]: %s",
            proof.min_val,
            proof.max_val,
            "VALID" if is_valid else "INVALID",
        )
        return VerificationResult(
            is_valid=is_valid,
            proof_type="range",
            verified_at=time.time(),
            details=f"CORTEX confirmed to have knowledge count in [{proof.min_val}, {proof.max_val}]."
            if is_valid
            else "Range proof structural check FAILED.",
        )

    def verify_commitment(
        self,
        commitment: KnowledgeCommitment,
        revealed_secret: str,
        revealed_blinding_hex: str,
    ) -> VerificationResult:
        """
        Verifica que un commitment corresponde al secreto revelado.

        Este método se usa cuando el Prover decide ABRIR el commitment
        para una auditoría específica. La apertura es soberana — CORTEX decide.

        Args:
            commitment: El commitment público previamente emitido.
            revealed_secret: El secreto que el Prover ahora revela.
            revealed_blinding_hex: El blinding factor para verificación.
        """
        try:
            blinding = bytes.fromhex(revealed_blinding_hex)
        except ValueError as e:
            return VerificationResult(
                is_valid=False,
                proof_type="commitment_opening",
                verified_at=time.time(),
                details=f"Invalid blinding factor hex: {e}",
            )

        is_valid = commitment.verify(revealed_secret, blinding)
        logger.info(
            "Commitment opening verification: %s", "VALID" if is_valid else "INVALID (tampered?)"
        )
        return VerificationResult(
            is_valid=is_valid,
            proof_type="commitment_opening",
            verified_at=time.time(),
            details="Commitment opens correctly — secret is authentic."
            if is_valid
            else "Commitment DOES NOT match the revealed secret. ALERT: possible forgery.",
        )

    def audit_report(self, results: list[VerificationResult]) -> dict[str, object]:
        """
        Genera un informe de auditoría agregado. Sin datos privados.
        """
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        return {
            "total_proofs_verified": total,
            "valid": valid,
            "invalid": total - valid,
            "validity_rate": valid / total if total > 0 else 0.0,
            "proof_types": list({r.proof_type for r in results}),
            "root_pin": self._expected_root,
            "generated_at": time.time(),
        }
