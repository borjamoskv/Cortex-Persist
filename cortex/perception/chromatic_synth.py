"""
CORTEX v5.0 — Chromatic Synthesizer (Synesthetic Transducer).

Maps RGB color space to audible sound patches.
Input:  RGB tuple (0-255)
Output: WAV file (44.1kHz, 16-bit stereo)

Mapping Architecture:
    R (0-255) → Low frequency (55-220 Hz), warm harmonics, compression
    G (0-255) → Mid frequency (220-880 Hz), stable timbre, clean
    B (0-255) → High frequency (880-4000 Hz), airy, reverb tail

    Luminosity (avg RGB) → Volume (0.0-1.0)
    Saturation  → Distortion amount (harmonic richness)
    Hue angle   → Stereo panning
"""

import math
import os
from dataclasses import dataclass
from typing import Tuple

import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 44100
DURATION_S = 3.0


@dataclass
class ChromaticPatch:
    """A synthesized sound patch derived from a single RGB color."""

    r: int
    g: int
    b: int
    freq_low: float
    freq_mid: float
    freq_high: float
    volume: float
    saturation: float
    hue_deg: float
    name: str


def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert RGB (0-255) to HSL (hue 0-360, sat 0-1, lum 0-1)."""
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(rf, gf, bf), min(rf, gf, bf)
    lum = (mx + mn) / 2.0
    if mx == mn:
        hue = sat = 0.0
    else:
        d = mx - mn
        sat = d / (2.0 - mx - mn) if lum > 0.5 else d / (mx + mn)
        if mx == rf:
            hue = (gf - bf) / d + (6.0 if gf < bf else 0.0)
        elif mx == gf:
            hue = (bf - rf) / d + 2.0
        else:
            hue = (rf - gf) / d + 4.0
        hue *= 60.0
    return hue, sat, lum


def _soft_clip(signal: np.ndarray, drive: float) -> np.ndarray:
    """Soft saturation distortion (tanh waveshaping)."""
    return np.tanh(signal * (1.0 + drive * 4.0))


def _simple_reverb(signal: np.ndarray, decay: float = 0.3, delay_ms: float = 40.0) -> np.ndarray:
    """Primitive comb-filter reverb for spatial width."""
    delay_samples = int(SAMPLE_RATE * delay_ms / 1000.0)
    out = signal.copy()
    for i in range(delay_samples, len(signal)):
        out[i] += decay * out[i - delay_samples]
    # Normalize to prevent clipping
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out / peak
    return out


def _envelope(length: int, attack_s: float = 0.05, release_s: float = 0.8) -> np.ndarray:
    """ADSR-ish envelope (Attack + Sustain + Release)."""
    env = np.ones(length, dtype=np.float64)
    attack_samples = int(SAMPLE_RATE * attack_s)
    release_samples = int(SAMPLE_RATE * release_s)

    # Attack ramp
    if attack_samples > 0:
        env[:attack_samples] = np.linspace(0, 1, attack_samples)

    # Release ramp
    if release_samples > 0 and release_samples < length:
        env[-release_samples:] = np.linspace(1, 0, release_samples)

    return env


def synthesize_color(r: int, g: int, b: int, duration: float = DURATION_S) -> Tuple[ChromaticPatch, np.ndarray]:
    """
    Core transduction: RGB → Audio waveform.

    Returns the patch metadata and the stereo audio signal (float64, -1 to 1).
    """
    hue, sat, lum = rgb_to_hsl(r, g, b)
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # --- Frequency Mapping ---
    # R channel → Low register (55 Hz - 220 Hz)
    freq_low = 55.0 + (r / 255.0) * 165.0
    # G channel → Mid register (220 Hz - 880 Hz)
    freq_mid = 220.0 + (g / 255.0) * 660.0
    # B channel → High register (880 Hz - 4000 Hz)
    freq_high = 880.0 + (b / 255.0) * 3120.0

    # --- Oscillators ---
    # Red: warm saw-like wave (fundamental + odd harmonics)
    osc_low = (
        np.sin(2 * np.pi * freq_low * t)
        + 0.5 * np.sin(2 * np.pi * freq_low * 2 * t)
        + 0.25 * np.sin(2 * np.pi * freq_low * 3 * t)
    )
    # Green: clean sine (stability)
    osc_mid = np.sin(2 * np.pi * freq_mid * t)
    # Blue: triangle-ish (airy, fewer harsh harmonics)
    osc_high = np.sin(2 * np.pi * freq_high * t) + 0.3 * np.sin(2 * np.pi * freq_high * 3 * t)

    # --- Amplitude by channel intensity ---
    amp_r = r / 255.0
    amp_g = g / 255.0
    amp_b = b / 255.0

    mix = (osc_low * amp_r * 0.5) + (osc_mid * amp_g * 0.35) + (osc_high * amp_b * 0.15)

    # --- Saturation → Distortion ---
    if sat > 0.1:
        mix = _soft_clip(mix, sat)

    # --- Blue dominance → Reverb tail ---
    reverb_amount = (b / 255.0) * 0.5
    if reverb_amount > 0.05:
        mix = _simple_reverb(mix, decay=reverb_amount, delay_ms=35)

    # --- Luminosity → Volume ---
    volume = max(0.05, lum)
    mix = mix * volume

    # --- Envelope ---
    env = _envelope(n_samples, attack_s=0.02, release_s=duration * 0.4)
    mix = mix * env

    # --- Hue → Stereo Panning ---
    # 0° (red) = left, 120° (green) = center, 240° (blue) = right
    pan = (hue % 360) / 360.0  # 0-1
    left = mix * math.cos(pan * math.pi / 2)
    right = mix * math.sin(pan * math.pi / 2)
    stereo = np.column_stack([left, right])

    # Normalize to prevent clipping
    peak = np.max(np.abs(stereo))
    if peak > 0:
        stereo = stereo / peak * 0.95

    patch = ChromaticPatch(
        r=r, g=g, b=b,
        freq_low=round(freq_low, 1),
        freq_mid=round(freq_mid, 1),
        freq_high=round(freq_high, 1),
        volume=round(volume, 2),
        saturation=round(sat, 2),
        hue_deg=round(hue, 1),
        name=f"chroma_{r:03d}_{g:03d}_{b:03d}"
    )

    return patch, stereo


def color_to_wav(
    r: int, g: int, b: int,
    output_dir: str = "/tmp/chromatic_synth",
    duration: float = DURATION_S
) -> str:
    """Full pipeline: RGB → WAV file on disk. Returns filepath."""
    os.makedirs(output_dir, exist_ok=True)
    patch, audio = synthesize_color(r, g, b, duration)

    # Convert to 16-bit PCM
    audio_16 = (audio * 32767).astype(np.int16)
    filepath = os.path.join(output_dir, f"{patch.name}.wav")
    wavfile.write(filepath, SAMPLE_RATE, audio_16)
    return filepath


# --- Palette Mode: Paint a full palette as a sequence ---

def palette_to_wav(
    colors: list,
    output_path: str = "/tmp/chromatic_synth/palette.wav",
    note_duration: float = 2.0,
    crossfade_s: float = 0.3
) -> str:
    """
    Render a list of RGB tuples as a continuous audio sequence.
    Each color becomes a note. Adjacent notes crossfade.
    """
    segments = []
    for r, g, b in colors:
        _, audio = synthesize_color(r, g, b, note_duration)
        segments.append(audio)

    # Concatenate with crossfade
    cf_samples = int(SAMPLE_RATE * crossfade_s)
    full = segments[0]
    for seg in segments[1:]:
        # Fade out tail of current
        full[-cf_samples:] *= np.linspace(1, 0, cf_samples)[:, np.newaxis]
        # Fade in head of next
        seg[:cf_samples] *= np.linspace(0, 1, cf_samples)[:, np.newaxis]
        # Overlap-add
        overlap = full[-cf_samples:] + seg[:cf_samples]
        full = np.concatenate([full[:-cf_samples], overlap, seg[cf_samples:]])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    audio_16 = (full / np.max(np.abs(full)) * 32767 * 0.95).astype(np.int16)
    wavfile.write(output_path, SAMPLE_RATE, audio_16)
    return output_path


if __name__ == "__main__":
    # Demo: Industrial Noir palette
    INDUSTRIAL_NOIR = [
        (10, 10, 10),      # #0A0A0A — Void Black
        (26, 26, 26),      # #1A1A1A — Carbon
        (204, 255, 0),     # #CCFF00 — Cyber Lime
        (212, 175, 55),    # #D4AF37 — Gold
        (46, 80, 144),     # #2E5090 — YInMn Blue
        (102, 0, 255),     # #6600FF — Sovereign Violet
    ]

    print("🎨→🔊 Chromatic Synthesizer — Industrial Noir Palette")
    print("=" * 55)

    for color in INDUSTRIAL_NOIR:
        path = color_to_wav(*color)
        patch, _ = synthesize_color(*color)
        print(
            f"  #{color[0]:02X}{color[1]:02X}{color[2]:02X} → "
            f"{patch.freq_low}Hz / {patch.freq_mid}Hz / {patch.freq_high}Hz "
            f"| Vol: {patch.volume} | Sat: {patch.saturation} | {path}"
        )

    palette_path = palette_to_wav(INDUSTRIAL_NOIR)
    print(f"\n🎶 Full palette sequence: {palette_path}")
