# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Algorithmic Music OMEGA (Procedural Synthesis)

Transforms mathematical invariants into structural acoustic waves (PCM).
Output is strictly quarantined to ~/BOCETOS to contain entropy.
"""

import math
import os
import random
from pathlib import Path

import numpy as np
import soundfile as sf

class ProceduralSynth:
    """Mathematical Waveform Generator."""
    
    def __init__(self, sample_rate: int = 44100):
        self.sr = sample_rate
        
    def generate_sine(self, freq: float, duration: float) -> np.ndarray:
        t = np.linspace(0, duration, int(self.sr * duration), endpoint=False)
        return np.sin(2 * np.pi * freq * t)
        
    def generate_square(self, freq: float, duration: float) -> np.ndarray:
        t = np.linspace(0, duration, int(self.sr * duration), endpoint=False)
        return np.sign(np.sin(2 * np.pi * freq * t))
        
    def apply_adsr(self, wave: np.ndarray, a: float=0.1, d: float=0.1, s_level: float=0.7, r: float=0.2) -> np.ndarray:
        """Apply Attack, Decay, Sustain, Release envelope."""
        total_samples = len(wave)
        a_samples = int(a * self.sr)
        d_samples = int(d * self.sr)
        r_samples = int(r * self.sr)
        
        # If the note is too short for the envelope, scale it down
        if a_samples + d_samples + r_samples > total_samples:
            a_samples = int(total_samples * 0.1)
            d_samples = int(total_samples * 0.1)
            r_samples = int(total_samples * 0.2)
            
        s_samples = total_samples - (a_samples + d_samples + r_samples)
        
        env_a = np.linspace(0, 1, a_samples)
        env_d = np.linspace(1, s_level, d_samples)
        env_s = np.full(s_samples, s_level)
        env_r = np.linspace(s_level, 0, r_samples)
        
        envelope = np.concatenate([env_a, env_d, env_s, env_r])
        return wave * envelope

class MarkovComposer:
    """Generates structural sequences using stochastic matrices."""
    
    def __init__(self):
        # Pentatonic minor A: A, C, D, E, G
        self.scale = [220.0, 261.63, 293.66, 329.63, 392.00, 440.0]
        # Probability matrix (Markov Chain)
        self.transitions = {
            0: [0.1, 0.4, 0.2, 0.2, 0.1, 0.0],
            1: [0.3, 0.1, 0.4, 0.1, 0.1, 0.0],
            2: [0.2, 0.3, 0.1, 0.3, 0.1, 0.0],
            3: [0.1, 0.2, 0.3, 0.1, 0.2, 0.1],
            4: [0.1, 0.1, 0.2, 0.3, 0.1, 0.2],
            5: [0.4, 0.0, 0.0, 0.1, 0.4, 0.1],
        }
        
    def generate_sequence(self, steps: int) -> list[float]:
        seq = []
        current = 0 # Start at root
        for _ in range(steps):
            seq.append(self.scale[current])
            current = random.choices(range(6), weights=self.transitions[current])[0]
        return seq

def execute_synthesis(output_filename: str = "cortex_procedural_001.wav"):
    """Orchestrates synthesis and anchors the result in BOCETOS quarantine."""
    synth = ProceduralSynth()
    composer = MarkovComposer()
    
    # 1. Generate Composition Data
    steps = 16
    note_duration = 0.25 # 120 BPM 8th notes
    frequencies = composer.generate_sequence(steps)
    
    # 2. Render PCM Waveform
    master_track = np.array([])
    for freq in frequencies:
        wave = synth.generate_sine(freq, note_duration)
        wave = synth.apply_adsr(wave, a=0.05, d=0.05, s_level=0.5, r=0.1)
        master_track = np.concatenate([master_track, wave])
        
    # L2 Normalization to prevent clipping (-1.0 to 1.0)
    max_amp = np.max(np.abs(master_track))
    if max_amp > 0:
        master_track = master_track / max_amp
        
    # 3. Quarantine (Rule L3)
    bocetos_dir = Path.home() / "BOCETOS"
    bocetos_dir.mkdir(parents=True, exist_ok=True)
    
    out_path = bocetos_dir / output_filename
    sf.write(out_path, master_track, synth.sr)
    
    print(f"[C5-REAL] Procedural synthesis complete. Entropy quarantined to: {out_path}")
    return out_path

if __name__ == "__main__":
    execute_synthesis()
