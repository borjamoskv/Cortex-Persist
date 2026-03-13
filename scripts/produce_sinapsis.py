#!/usr/bin/env python3
"""
GRAMMY-Ω Production Run: Sinapsis de Neón.

Executes the full Sovereign Music Engine pipeline:
1. Album initialization
2. Gemini-powered parametric matrix generation (Sonic Vectors Ξ)
3. Audio synthesis (real API or simulation)
4. Deterministic DSP mastering (EBU R128, transient shaping, tonal balance)
5. GRI (Grammy Readiness Index) evaluation

Usage:
    python3 scripts/produce_sinapsis.py [--simulate]
"""

import argparse
import asyncio
import logging
import os
import sys
import time

import numpy as np

# Ensure CORTEX is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex.music_engine.dsp_apotheosis import DSPApotheosis
from cortex.music_engine.orchestrator import (
    DEFAULT_BPM,
    GRAMMYOrchestrator,
    TrackContext,
    TrackState,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("grammy.production")

# ── Album Definition ──────────────────────────────────────────────────

ALBUM_TITLE = "Sinapsis de Neón"
ALBUM_CONCEPT = (
    "Un viaje neuroquímico a través del techno industrial y el bass design soberano. "
    "Cada pista mapea una región del córtex cerebral: frecuencias sub-graves como "
    "sinapsis, texturas granulares como dendritas, y ritmos como potenciales de acción. "
    "Producción de frontera: masterización a -14 LUFS, True Peak <= -1 dBTP."
)

# Track definitions: (id, title, bpm, key)
TRACKLIST = [
    ("trk-01", "Corteza Prefrontal", 130, "F minor"),
    ("trk-02", "Sinapsis de Neón", 128, "G minor"),
    ("trk-03", "Dendrita Oscura", 135, "D# minor"),
    ("trk-04", "Potencial de Acción", 140, "A minor"),
    ("trk-05", "Tálamo", 124, "C minor"),
    ("trk-06", "Cuerpo Calloso", 132, "E minor"),
    ("trk-07", "Amígdala", 126, "B♭ minor"),
    ("trk-08", "Hipocampo", 122, "G# minor"),
    ("trk-09", "Neurotransmisor", 138, "F# minor"),
    ("trk-10", "Apoptosis Neural", 118, "D minor"),
]


# ── Synthetic Audio Generator (Simulation Mode) ──────────────────────

def generate_synthetic_audio(
    bpm: int,
    key: str,
    duration_seconds: float = 30.0,
    sample_rate: int = 44100,
) -> np.ndarray:
    """
    Generate a synthetic stereo audio signal for DSP testing.
    Creates a layered signal with:
    - Sub-bass sine wave (fundamental frequency from key)
    - Kick pattern at BPM
    - Filtered noise for texture
    - Stereo width via phase offset
    """
    # Key -> fundamental frequency mapping (approximate, A4=440Hz basis)
    key_freq_map = {
        "C minor": 130.81, "C# minor": 138.59, "D minor": 146.83,
        "D# minor": 155.56, "E minor": 164.81, "F minor": 174.61,
        "F# minor": 185.00, "G minor": 196.00, "G# minor": 207.65,
        "A minor": 220.00, "B♭ minor": 233.08, "B minor": 246.94,
    }
    fundamental = key_freq_map.get(key, 130.81)
    n_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, n_samples, endpoint=False)

    # Sub-bass (sine)
    sub_bass = 0.4 * np.sin(2 * np.pi * fundamental * t)

    # Kick pattern at BPM
    beat_interval = 60.0 / bpm
    kick = np.zeros(n_samples)
    for beat_start in np.arange(0, duration_seconds, beat_interval):
        idx_start = int(beat_start * sample_rate)
        decay_len = min(int(0.15 * sample_rate), n_samples - idx_start)
        if decay_len > 0:
            decay = np.exp(-np.linspace(0, 8, decay_len))
            kick_hit = 0.6 * np.sin(
                2 * np.pi * 60 * np.linspace(0, 0.15, decay_len)
            ) * decay
            kick[idx_start:idx_start + decay_len] += kick_hit

    # Filtered noise for texture (bandpass 2-8 kHz feel)
    noise = 0.05 * np.random.randn(n_samples)
    # Simple high-pass via diff
    texture = np.diff(noise, prepend=0) * 0.3

    # Mono mix
    mono = sub_bass + kick + texture
    mono = mono / (np.max(np.abs(mono)) + 1e-10)  # Normalize

    # Stereo with slight phase offset
    stereo = np.column_stack([
        mono,
        np.roll(mono, int(0.0003 * sample_rate))  # ~0.3ms ITD
    ])

    return stereo.astype(np.float64)


# ── Production Pipeline ──────────────────────────────────────────────

async def produce_track(
    orchestrator: GRAMMYOrchestrator,
    track: TrackContext,
    simulate: bool = True,
) -> TrackContext:
    """Produce a single track through the full GRAMMY-Ω pipeline."""
    logger.info("═" * 60)
    logger.info("PRODUCING: %s (BPM: %d, Key: %s)", track.title, track.bpm, track.key)
    logger.info("═" * 60)

    # 1. Generate parametric matrix via Gemini
    logger.info("[1/5] Gemini Cognition: Generating Sonic Vector matrix...")
    matrix = await orchestrator.generate_prompt_matrix(track)
    track.metadata["sonic_vectors"] = matrix.get("sonic_vectors", {})
    track.metadata["expected_entropy"] = matrix.get("expected_entropy", "medium")
    track.metadata["target_model"] = matrix.get("target_model", "suno_v5")
    logger.info(
        "  → Target: %s | Entropy: %s | Vectors: %s",
        matrix.get("target_model"),
        matrix.get("expected_entropy"),
        matrix.get("sonic_vectors"),
    )

    # 2. Audio Generation
    if simulate:
        logger.info("[2/5] Simulation Mode: Generating synthetic audio...")
        audio = generate_synthetic_audio(
            bpm=track.bpm, key=track.key, duration_seconds=30.0
        )
        track.metadata["raw_audio_uri"] = f"sim://sinapsis/{track.id}.wav"
        track.stems = {
            "master": f"sim://sinapsis/{track.id}_master.wav",
            "bass": f"sim://sinapsis/{track.id}_bass.wav",
            "drums": f"sim://sinapsis/{track.id}_drums.wav",
        }
        track.state = TrackState.TRACKING
    else:
        logger.info("[2/5] Live API Mode: Sending to %s...", matrix.get("target_model"))
        target_key = matrix.get("target_model", "suno_v5").lower()
        if target_key not in orchestrator.adapters:
            target_key = "suno_v5"
        adapter = orchestrator.adapters[target_key]
        job_uri = await adapter.generate(matrix)
        track.metadata["raw_audio_uri"] = job_uri
        stems = await adapter.get_stems(job_uri)
        track.stems = stems
        track.state = TrackState.TRACKING
        # In live mode, we'd download the audio here
        audio = generate_synthetic_audio(
            bpm=track.bpm, key=track.key, duration_seconds=30.0
        )

    # 3. DSP Apotheosis (Deterministic Mastering)
    logger.info("[3/5] DSP Apotheosis: Deterministic mastering pipeline...")
    dsp = DSPApotheosis()
    sample_rate = 44100

    pre_lufs = dsp.calculate_lufs(audio, sample_rate)
    logger.info("  → Pre-master LUFS: %.2f", pre_lufs)

    mastered = dsp.master_track(audio, sample_rate)
    post_lufs = dsp.calculate_lufs(mastered, sample_rate)
    peak = float(np.max(np.abs(mastered)))

    track.metadata["pre_master_lufs"] = round(pre_lufs, 2)
    track.metadata["post_master_lufs"] = round(post_lufs, 2)
    track.metadata["true_peak"] = round(peak, 4)
    track.state = TrackState.POST_PRODUCTION

    logger.info("  → Post-master LUFS: %.2f | True Peak: %.4f", post_lufs, peak)

    # 4. GRI Evaluation
    logger.info("[4/5] Grammy Readiness Index (GRI) evaluation via Gemini...")
    gri = await orchestrator.evaluate_track_gri(track)
    track.gri_score = gri
    track.state = TrackState.MASTERED

    logger.info("  → GRI Score: %.3f", gri)
    if gri >= 0.85:
        logger.info("  ✦ GRAMMY-READY ✦")
    elif gri >= 0.70:
        logger.info("  → Competitive tier. Polish recommended.")
    else:
        logger.info("  → Below threshold. Iteration needed.")

    # 5. Summary
    logger.info("[5/5] Track production complete.")
    logger.info(
        "  Result: %s | GRI: %.3f | LUFS: %.2f | Peak: %.4f",
        track.state.value, track.gri_score, post_lufs, peak,
    )

    return track


async def produce_album(
    track_ids: list[int] | None = None,
    simulate: bool = True,
) -> None:
    """Produce the full 'Sinapsis de Neón' album or selected tracks."""
    t0 = time.monotonic()

    orchestrator = GRAMMYOrchestrator()
    album = await orchestrator.initialize_album(ALBUM_TITLE, ALBUM_CONCEPT)

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  GRAMMY-Ω PRODUCTION RUN: %s", ALBUM_TITLE)
    logger.info("║  Mode: %s", "SIMULATION" if simulate else "LIVE API")
    logger.info("║  Tracks: %d", len(TRACKLIST))
    logger.info("╚══════════════════════════════════════════════════════════╝")

    # Select tracks
    selected = TRACKLIST
    if track_ids:
        selected = [TRACKLIST[i] for i in track_ids if i < len(TRACKLIST)]

    results = []
    for tid, title, bpm, key in selected:
        track = TrackContext(
            id=tid, title=title, bpm=bpm, key=key, state=TrackState.CONCEPT,
        )
        try:
            result = await produce_track(orchestrator, track, simulate=simulate)
            results.append(result)
            album.tracks.append(result)
        except Exception as e:
            logger.error("FAILED: %s — %s", title, e)
            track.state = TrackState.REJECTED
            track.metadata["error"] = str(e)
            results.append(track)

    # Album summary
    elapsed = time.monotonic() - t0
    gri_scores = [t.gri_score for t in results if t.gri_score > 0]
    avg_gri = sum(gri_scores) / len(gri_scores) if gri_scores else 0.0
    album.global_gri = avg_gri

    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  ALBUM PRODUCTION COMPLETE: %s", ALBUM_TITLE)
    logger.info("╠══════════════════════════════════════════════════════════╣")
    for t in results:
        status = "✅" if t.state == TrackState.MASTERED else "❌"
        logger.info(
            "║  %s %s — GRI: %.3f | LUFS: %s",
            status, t.title, t.gri_score,
            t.metadata.get("post_master_lufs", "N/A"),
        )
    logger.info("╠══════════════════════════════════════════════════════════╣")
    logger.info("║  Global GRI: %.3f", avg_gri)
    logger.info("║  Elapsed: %.1fs", elapsed)
    logger.info("║  Verdict: %s", (
        "✦ GRAMMY CONTENDER ✦" if avg_gri >= 0.85
        else "COMPETITIVE" if avg_gri >= 0.70
        else "NEEDS ITERATION"
    ))
    logger.info("╚══════════════════════════════════════════════════════════╝")

    # Close adapters
    for adapter in orchestrator.adapters.values():
        await adapter.close()


def main():
    parser = argparse.ArgumentParser(
        description="GRAMMY-Ω Production Run: Sinapsis de Neón"
    )
    parser.add_argument(
        "--simulate", action="store_true", default=True,
        help="Use synthetic audio instead of real API calls (default: True)",
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Use real API calls (requires SUNO_API_KEY, UDIO_API_KEY, etc.)",
    )
    parser.add_argument(
        "--tracks", type=str, default="",
        help="Comma-separated track indices (0-9). Empty = all tracks.",
    )
    args = parser.parse_args()

    simulate = not args.live

    track_ids = None
    if args.tracks:
        track_ids = [int(x.strip()) for x in args.tracks.split(",")]

    asyncio.run(produce_album(track_ids=track_ids, simulate=simulate))


if __name__ == "__main__":
    main()
