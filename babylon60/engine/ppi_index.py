import json
import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)

class PPILevel(IntEnum):
    ZERO = 0       # Pure speculation, "Green Theater"
    LOW = 1        # Weak circumstantial evidence
    MODERATE = 2   # Plausible but unverified
    STRONG = 3     # Cryptographic or physical trace
    ABSOLUTE = 4   # Immutable consensus / Ledger
    C5_REAL = 5    # Transacción bancaria, hardware state

@dataclass
class PPIScore:
    reality: PPILevel
    risk: PPILevel
    evidence: PPILevel

    @property
    def total_score(self) -> float:
        return (self.reality + self.risk + self.evidence) / 15.0

    def is_valid(self, threshold: float = 0.6) -> bool:
        return self.total_score >= threshold

class PPIIndex:
    """
    APEX-012: Destrucción de Ilusión Forense (PPI Index).
    Toda afirmación (OSINT/Jurídica) pasa por la métrica PPI (0-5) bajo los ejes Reality, Risk, Evidence.
    La prueba es la transacción bancaria o el log criptográfico, no el texto del brochure.
    """
    
    def __init__(self):
        self.evidence_keywords = {
            PPILevel.C5_REAL: ["banco", "transacción", "hash", "commit", "ledger", "mmap", "físico", "hardware"],
            PPILevel.ABSOLUTE: ["firma", "criptográfico", "ed25519", "consenso", "wal"],
            PPILevel.STRONG: ["log", "traza", "métrica", "auditoría", "sistema"],
            PPILevel.MODERATE: ["reporte", "análisis", "declaración", "documento"],
            PPILevel.LOW: ["creo", "posible", "quizás", "probablemente", "promesa"],
            PPILevel.ZERO: ["ilusión", "teatro", "simulación", "brochure", "marketing"]
        }

    def evaluate_claim(self, claim_text: str, evidence_payload: dict[str, Any]) -> PPIScore:
        """
        Evalúa una afirmación y su evidencia adjunta.
        """
        claim_text.lower()
        evidence_str = json.dumps(evidence_payload).lower()
        
        # 1. Evaluate Evidence (0-5)
        evidence_score = PPILevel.ZERO
        for level in reversed(list(PPILevel)):
            if any(kw in evidence_str for kw in self.evidence_keywords[level]):
                evidence_score = level
                break
                
        # 2. Evaluate Reality (Is it structural or just narrative?)
        reality_score = PPILevel.ZERO
        if "hash" in evidence_payload or "transaction_id" in evidence_payload:
            reality_score = PPILevel.C5_REAL
        elif "timestamp" in evidence_payload and "signature" in evidence_payload:
            reality_score = PPILevel.ABSOLUTE
        elif len(evidence_payload.keys()) > 3:
            reality_score = PPILevel.STRONG
        elif len(evidence_payload.keys()) > 0:
            reality_score = PPILevel.MODERATE
            
        # 3. Evaluate Risk (Skin in the game)
        risk_score = PPILevel.ZERO
        if "financial_exposure" in evidence_payload or "slashing_condition" in evidence_payload:
            risk_score = PPILevel.C5_REAL
        elif "reputation_stake" in evidence_payload:
            risk_score = PPILevel.STRONG
        elif "accountability" in evidence_payload:
            risk_score = PPILevel.MODERATE
            
        score = PPIScore(reality=reality_score, risk=risk_score, evidence=evidence_score)
        
        logger.info(f"PPI Evaluation: {score.total_score:.2f} (R:{score.reality.value} Rk:{score.risk.value} E:{score.evidence.value})")
        return score
        
    def enforce_reality(self, claim_text: str, evidence_payload: dict[str, Any], min_score: float = 0.6) -> bool:
        """
        Destruye la ilusión forense: o pasas el threshold de PPI o la afirmación es descartada.
        """
        score = self.evaluate_claim(claim_text, evidence_payload)
        if not score.is_valid(min_score):
            logger.warning(f"Forensic Illusion Destroyed: Claim '{claim_text}' failed PPI threshold ({score.total_score:.2f} < {min_score})")
            return False
        return True
