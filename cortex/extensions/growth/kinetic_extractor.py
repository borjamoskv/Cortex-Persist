# [C5-REAL] Exergy-Maximized
"""
Kinetic Notes Extractor - Endogenous Growth Engine
Applies Thermodynamic Context Compression (Landauer's Principle) to long-form
newsletters to extract high-exergy pills (Notes) for organic exposure.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger("cortex.extensions.growth.kinetic_extractor")

@dataclass
class ExergyNote:
    content: str
    shannon_entropy_score: float
    original_paragraph_ref: str

class KineticExtractor:
    """
    Extracts dense signals from noisy markdown text.
    Bypasses green theater and narrative structures to isolate structural invariants
    that perform optimally on algorithmic feeds (Substack Notes/X).
    """

    def __init__(self, target_max_length: int = 280):
        self.target_max_length = target_max_length
        # Purgamos padding phrases.
        self.anergy_stop_words = [
            "en conclusión", "como he dicho", "por otro lado", "es importante notar que",
            "en resumen", "para finalizar", "quizás", "probablemente", "a mi modo de ver"
        ]

    def _purge_anergy(self, paragraph: str) -> str:
        """Removes low-yield conversational padding."""
        cleaned = paragraph
        for word in self.anergy_stop_words:
            cleaned = cleaned.replace(word, "").replace(word.capitalize(), "")
        return cleaned.strip()

    def _evaluate_density(self, text: str) -> float:
        """
        Heuristic evaluation of Shannon Entropy in the text.
        Higher score means more concepts per character.
        """
        if not text:
            return 0.0
        unique_words = len(set(text.lower().split()))
        total_words = len(text.split())
        if total_words == 0:
            return 0.0
        # Simplistic density score: unique words ratio combined with length constraint
        ratio = unique_words / total_words
        length_penalty = 1.0 if len(text) <= self.target_max_length else (self.target_max_length / len(text))
        return round(ratio * length_penalty * 100, 2)

    def extract_notes(self, markdown_content: str) -> List[ExergyNote]:
        """
        Parses full newsletter content and returns a list of high-exergy notes.
        """
        paragraphs = [p.strip() for p in markdown_content.split('\n\n') if len(p.strip()) > 50]
        notes = []

        for p in paragraphs:
            # Skip code blocks and headers
            if p.startswith('```') or p.startswith('#'):
                continue
            
            purged = self._purge_anergy(p)
            density = self._evaluate_density(purged)
            
            # If paragraph is dense enough and within size limits, it's a valid note
            if density > 65.0 and len(purged) <= self.target_max_length * 1.5:
                # We cap it synthetically if slightly above
                final_content = purged[:self.target_max_length]
                notes.append(ExergyNote(
                    content=final_content,
                    shannon_entropy_score=density,
                    original_paragraph_ref=p[:30] + "..."
                ))

        # Sort by density (highest first)
        notes.sort(key=lambda n: n.shannon_entropy_score, reverse=True)
        logger.info("Extracted %d Exergy Notes from content.", len(notes))
        return notes

def execute_extraction(filepath: str) -> List[ExergyNote]:
    """Helper entrypoint for the CLI/Agent bus."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    extractor = KineticExtractor()
    return extractor.extract_notes(content)
