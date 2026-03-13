"""Synthesizer primitives for MIDI rendering.

Extracted from midi_engine.py for LOC compliance (AX-011).
"""

from __future__ import annotations

import numpy as np

DEFAULT_SR = 44100

def _synth_sine(freq: float, duration_s: float, sr: int = DEFAULT_SR) -> np.ndarray:
    """Generate a sine wave."""
    t = np.arange(int(sr * duration_s)) / sr
    return np.sin(2 * np.pi * freq * t)


def _synth_square(freq: float, duration_s: float, sr: int = DEFAULT_SR) -> np.ndarray:
    """Generate a square wave."""
    t = np.arange(int(sr * duration_s)) / sr
    return np.sign(np.sin(2 * np.pi * freq * t))


def _synth_kick(sr: int = DEFAULT_SR) -> np.ndarray:
    """Synthesize a kick drum: pitch-sweeping sine from 150Hz to 45Hz."""
    duration_s = KICK_DECAY_MS / 1000.0
    n_samples = int(sr * duration_s)
    t = np.arange(n_samples) / sr

    # Exponential frequency sweep
    freq = KICK_FREQ_START * np.exp(-t * np.log(KICK_FREQ_START / KICK_FREQ_END) / duration_s)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    wave = np.sin(phase)

    # Exponential amplitude decay
    envelope = np.exp(-t * 5.0 / duration_s)
    return wave * envelope * KICK_AMPLITUDE


def _synth_snare(sr: int = DEFAULT_SR) -> np.ndarray:
    """Synthesize a snare: body tone + filtered noise burst."""
    duration_s = SNARE_NOISE_MS / 1000.0
    n_samples = int(sr * duration_s)
    t = np.arange(n_samples) / sr

    # Body: 180Hz sine with fast decay
    body = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 20)

    # Noise: white noise with envelope
    noise = np.random.randn(n_samples) * np.exp(-t * 12)

    return (body * 0.4 + noise * 0.6) * SNARE_AMPLITUDE


def _synth_hihat(sr: int = DEFAULT_SR) -> np.ndarray:
    """Synthesize a hi-hat: filtered noise burst, very short."""
    duration_s = HAT_NOISE_MS / 1000.0
    n_samples = int(sr * duration_s)
    t = np.arange(n_samples) / sr
    noise = np.random.randn(n_samples) * np.exp(-t * 40)
    return noise * HAT_AMPLITUDE


def _note_to_freq(note: int) -> float:
    """Convert MIDI note number to frequency (A4 = 440Hz)."""
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


