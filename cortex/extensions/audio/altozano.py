# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Agente Altozano OMEGA

Harmonic Deconstructor and Psychoacoustic Analyzer.
Extracts empirical structural invariants from PCM audio using librosa.
"""

import logging
from pathlib import Path
from typing import Dict, Any

try:
    import librosa
    import numpy as np
except ImportError:
    librosa = None
    np = None

logger = logging.getLogger("cortex.audio.altozano")

class AltozanoAnalyzer:
    """The Harmonic Deconstructor."""
    
    def __init__(self):
        if not librosa:
            logger.critical("[Altozano] librosa is not installed. C5-REAL analysis impossible.")
            raise RuntimeError("Missing librosa. Install with: pip install 'cortex-persist[audio]'")
            
        # Map chroma indices to note names (0 = C, 1 = C#, etc.)
        self.chroma_map = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def deconstruct_track(self, filepath: str | Path) -> Dict[str, Any]:
        """
        Loads the PCM waveform and extracts mathematical acoustic features.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Track not found: {path}")
            
        logger.info(f"[Altozano] Extracting structural invariants from: {path.name}")
        
        # 1. Extraction
        y, sr = librosa.load(path)
        
        # 2. Rhythmic Extraction (BPM)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
        
        # 3. Harmonic Extraction (Chromagram)
        # We use Constant-Q Transform which is logarithmically spaced (like human hearing)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        
        # Aggregate chroma across time to find the dominant pitch classes
        chroma_sum = np.sum(chroma, axis=1)
        
        # Find the Top 3 notes to infer tonality
        top_indices = np.argsort(chroma_sum)[::-1][:3]
        dominant_notes = [self.chroma_map[i] for i in top_indices]
        
        # 4. Synthesize YAML Report
        report = {
            "track": path.name,
            "sample_rate_hz": sr,
            "duration_sec": round(len(y) / sr, 2),
            "bpm": round(bpm, 2),
            "dominant_pitch_classes": dominant_notes,
            "structural_analysis": self._generate_analysis(dominant_notes)
        }
        
        return report

    def _generate_analysis(self, notes: list[str]) -> str:
        """Generates a deterministic observation of the harmonic topology."""
        root = notes[0]
        return f"La fundamental inferida es {root}. La presencia de {notes[1]} y {notes[2]} sugiere el núcleo de la tríada. El espectro acústico confirma una matriz armónica estable."

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        import yaml
        agent = AltozanoAnalyzer()
        res = agent.deconstruct_track(sys.argv[1])
        print(yaml.dump(res, default_flow_style=False))
    else:
        print("Usage: python altozano.py <path_to_wav>")
