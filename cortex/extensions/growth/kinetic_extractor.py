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
        True Shannon Entropy calculation (character-level distribution) combined with
        thermodynamic length penalties.
        """
        import math
        from collections import Counter
        
        if not text:
            return 0.0
            
        length = len(text)
        freq = Counter(text)
        entropy = -sum((count / length) * math.log2(count / length) for count in freq.values())
        
        # Max theoretical entropy for language is ~5.0. Normalize to a 100 scale.
        base_score = min(100.0, (entropy / 5.0) * 100.0)
        
        # Length thermodynamic boundaries
        if length > self.target_max_length:
            penalty = self.target_max_length / length
        elif length < 60:
            penalty = length / 60.0  # Penalize micro-fragments lacking context
        else:
            penalty = 1.0
            
        return round(base_score * penalty, 2)

    def extract_notes(self, markdown_content: str) -> List[ExergyNote]:
        """
        Parses full newsletter content and returns a list of high-exergy notes.
        """
        paragraphs = [p.strip() for p in markdown_content.split('\n\n') if len(p.strip()) > 30]
        notes = []

        for p in paragraphs:
            # Bypass Green Theater & Structural Noise (Headers, Lists, Comments, Code)
            if p.startswith(('```', '#', '<!--', '-', '*', '>')):
                continue
                
            # Filter low word-count fragments
            if len(p.split()) < 8:
                continue
            
            purged = self._purge_anergy(p)
            density = self._evaluate_density(purged)
            
            # Thermodynamic threshold and max length cap
            if density > 65.0 and len(purged) <= self.target_max_length * 1.5:
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

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Kinetic Extractor: Exergy-Maximized Notes")
    parser.add_argument("filepath", help="Path to the markdown newsletter")
    parser.add_argument("--outdir", default="queue/notes", help="Output directory for extracted notes")
    args = parser.parse_args()

    notes = execute_extraction(args.filepath)
    os.makedirs(args.outdir, exist_ok=True)
    
    saved_count = 0
    for i, note in enumerate(notes):
        # Strict thermodynamic cutoff (only save top-tier exergy)
        if note.shannon_entropy_score < 75.0:
            continue
        
        safe_score = str(note.shannon_entropy_score).replace('.', '_')
        filename = f"note_exergy_{safe_score}_{i}.md"
        outpath = os.path.join(args.outdir, filename)
        
        with open(outpath, 'w', encoding='utf-8') as f:
            f.write(f"<!-- Exergy Score: {note.shannon_entropy_score} | Source: {os.path.basename(args.filepath)} -->\n")
            f.write(f"{note.content}\n")
        saved_count += 1
        
    print(f"[C5-REAL] Extracted and crystallized {saved_count} High-Exergy Notes to {args.outdir}/")
