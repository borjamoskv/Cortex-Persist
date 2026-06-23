import re
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

@dataclass
class PREvaluation:
    social_engineering_score: float  # 0.0 to 1.0 (1.0 = highly manipulated)
    detected_markers: List[str]
    urgency_detected: bool
    manipulation_detected: bool
    is_safe: bool

class PRSocialEngineeringDetector:
    """
    APEX-044: Detección de Ingeniería Social en PRs.
    Audita los diffs y mensajes de commit en busca de urgencia fabricada,
    complejidad oculta bajo descripciones triviales, y manipulación emocional.
    """

    def __init__(self):
        # The psychology of a compromised developer or malicious actor
        self.urgency_markers = re.compile(r'\b(asap|urgent|hotfix|emergency|critical|broken production|pls merge|quick fix)\b', re.IGNORECASE)
        self.manipulation_markers = re.compile(r'\b(just a small|trivial|don\'t worry|trust me|boss wants|need this now|please help)\b', re.IGNORECASE)
        self.obfuscation_markers = re.compile(r'(eval\(|exec\(|base64|decode\(|subprocess|os\.system|__import__|getattr)', re.IGNORECASE)

    def analyze_pr(self, title: str, body: str, diff_content: str) -> PREvaluation:
        combined_text = f"{title} {body}"
        
        urgency_hits = self.urgency_markers.findall(combined_text)
        manipulation_hits = self.manipulation_markers.findall(combined_text)
        obfuscation_hits = self.obfuscation_markers.findall(diff_content)

        score = 0.0
        markers = []

        if urgency_hits:
            score += 0.4
            markers.extend([f"URGENCY({x})" for x in urgency_hits])
            
        if manipulation_hits:
            score += 0.3
            markers.extend([f"MANIPULATION({x})" for x in manipulation_hits])
            
        if obfuscation_hits:
            # If the PR claims to be trivial but contains obfuscation/eval, it's a massive red flag.
            if manipulation_hits or "trivial" in combined_text.lower():
                score += 0.8
                markers.append("TRIVIAL_OBFUSCATION_MISMATCH")
            else:
                score += 0.5
                markers.extend([f"DANGEROUS_CALL({x})" for x in obfuscation_hits])

        # Clamp score
        score = min(score, 1.0)
        
        is_safe = score < 0.6
        
        if not is_safe:
            logger.warning(f"APEX-044 Triggered: PR rejected due to high SE/Risk score ({score}). Markers: {markers}")
            
        return PREvaluation(
            social_engineering_score=score,
            detected_markers=markers,
            urgency_detected=len(urgency_hits) > 0,
            manipulation_detected=len(manipulation_hits) > 0,
            is_safe=is_safe
        )
