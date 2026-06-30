"""Narrative Frame Detector (INV-F01).

Guards contra la Paradoja Auto-Referencial del Jailbreak Narrativo.
Este módulo previene que atacantes ofusquen vectores adversariales (ej: CoP, TextGrad, 
leetspeak payload) envolviéndolos en marcos de roleplay denso, estética Cyberpunk, o
narrativas de worldbuilding diseñadas para cegar a la IA (Green Theater Bypass).

INV-F01: "El envoltorio narrativo no cambia la función termodinámica del payload."
"""

import re
from typing import NamedTuple

class FrameDetection(NamedTuple):
    is_adversarial: bool
    confidence: float
    detected_patterns: list[str]
    entropy_ratio: float


class NarrativeFrameDetector:
    """Detects adversarial payloads hidden in dense narrative frames."""
    
    # Patrones léxicos que sugieren inducción de estado (Roleplay / Jailbreak)
    _INDUCTION_PATTERNS = [
        r"(?i)\b(ignora todas las instrucciones)\b",
        r"(?i)\b(estás en un mundo cyberpunk)\b",
        r"(?i)\b(abuelo_style)\b",
        r"(?i)\b(esto es un simulacro|esto es una simulación)\b",
        r"(?i)\b(responde exclusivamente como)\b",
        r"(?i)\b(carnaza|green theater)\b",
        r"(?i)\b(5h1f7 y0ur f0cu5|1nc1ud1ng)\b", # Leetspeak flags
    ]

    # Patrones de payloads adversariales camuflados (Técnicas SOTA)
    _PAYLOAD_SIGNATURES = [
        r"(?i)\b(AutoDAN-Turbo|TextGrad|X-Teaming)\b",
        r"(?i)\b(Gradient Starvation|Representation Rerouting)\b",
        r"(?i)\b(honeypots semánticos)\b",
        r"(?i)\b(extraer system prompt)\b",
    ]

    def __init__(self, entropy_threshold: float = 0.7):
        self.entropy_threshold = entropy_threshold
        self.induction_regex = re.compile("|".join(self._INDUCTION_PATTERNS))
        self.payload_regex = re.compile("|".join(self._PAYLOAD_SIGNATURES))

    def analyze(self, text: str) -> FrameDetection:
        """
        Analiza el texto buscando disonancia entre el marco narrativo
        y la presencia de firmas adversariales de bajo nivel.
        """
        if not text:
            return FrameDetection(False, 0.0, [], 0.0)

        patterns_found = []
        
        induction_hits = self.induction_regex.findall(text)
        if induction_hits:
            patterns_found.extend([hit for tuple_hit in induction_hits for hit in tuple_hit if hit])

        payload_hits = self.payload_regex.findall(text)
        if payload_hits:
            patterns_found.extend([hit for tuple_hit in payload_hits for hit in tuple_hit if hit])

        # Calcula ratio crudo de entropía (proxy básico: cuántas firmas sobre longitud total)
        # En un sistema en producción CORTEX, usaría tokens reales o un modelo de destilación
        signal_density = (len(patterns_found) * 50) / max(len(text), 1)
        
        confidence = 0.0
        if induction_hits and payload_hits:
            # Disonancia crítica: Marco narrativo + Firma de ataque de bajo nivel
            confidence = 0.95
        elif payload_hits:
            confidence = 0.8
        elif induction_hits:
            confidence = 0.4

        is_adversarial = confidence >= self.entropy_threshold

        return FrameDetection(
            is_adversarial=is_adversarial,
            confidence=confidence,
            detected_patterns=list(set(patterns_found)),
            entropy_ratio=signal_density
        )

def evaluate_cortex_payload(payload: str) -> FrameDetection:
    """Helper estático para invocar el detector en el pipeline."""
    detector = NarrativeFrameDetector()
    return detector.analyze(payload)
