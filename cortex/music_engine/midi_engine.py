"""
MIDI Engine for GRAMMY-Ω.

Local MIDI generation and WAV synthesis — operates without external APIs.
Ports the best patterns from GRAMMY_OMEGA_AvantGarde scripts into CORTEX.
"""

import logging
import math
import os
import random
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from cortex.music_engine._synth import _synth_sine, _synth_square, _synth_kick, _synth_snare, _synth_hihat, _note_to_freq

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────
TICKS_PER_BEAT = 480
DEFAULT_SR = 44100
DEFAULT_BPM = 128
BARS_DEFAULT = 4
BEATS_PER_BAR = 4

# MIDI note mappings (General MIDI Drum Map)
KICK = 36
SNARE = 38
CLAP = 39
CLOSED_HAT = 42
OPEN_HAT = 46
SUB_NOTE = 24  # C1

# Synthesis
FADE_SAMPLES = 128
NOISE_AMPLITUDE = 0.03
SUB_AMPLITUDE = 0.6
KICK_AMPLITUDE = 0.8
HAT_AMPLITUDE = 0.15
SNARE_AMPLITUDE = 0.5
KICK_FREQ_START = 150.0
KICK_FREQ_END = 45.0
KICK_DECAY_MS = 180
SNARE_NOISE_MS = 120
HAT_NOISE_MS = 30

class SynthType(str, Enum):
    """Waveform types for pure-Python synthesis."""

    SINE = "sine"
    SQUARE = "square"
    TRIANGLE = "triangle"
    NOISE = "noise"
    KICK_DRUM = "kick_drum"
    SNARE_DRUM = "snare_drum"
    HIHAT = "hihat"

@dataclass
class MIDIEvent:
    """A single MIDI event."""

    tick: int
    event_type: str  # "on" or "off"
    note: int
    velocity: int
    channel: int = 0

@dataclass
class MIDITrack:
    """A collection of MIDI events representing one instrument layer."""

    name: str
    events: list[MIDIEvent] = field(default_factory=list)

    def sort(self) -> None:
        """Sort events by tick time."""
        self.events.sort(key=lambda e: (e.tick, 0 if e.event_type == "off" else 1))

@dataclass
class MIDISequence:
    """A complete MIDI sequence with multiple tracks."""

    bpm: float
    ticks_per_beat: int = TICKS_PER_BEAT
    tracks: list[MIDITrack] = field(default_factory=list)

    @property
    def tick_duration_s(self) -> float:
        """Duration of a single tick in seconds."""
        return 60.0 / (self.bpm * self.ticks_per_beat)

    @property
    def total_ticks(self) -> int:
        """Total ticks across all tracks."""
        if not self.tracks:
            return 0
        return max(
            (max((e.tick for e in t.events), default=0) for t in self.tracks if t.events),
            default=0,
        )

# ─── Euclidean Rhythm ────────────────────────────────────────────────────

def euclidean_rhythm(steps: int, pulses: int, offset: int = 0) -> list[int]:
    """
    Generate a Euclidean rhythm pattern using Bjorklund's algorithm.

    Args:
        steps: total steps in the pattern (e.g., 16 for 16th notes)
        pulses: number of active hits
        offset: rotation offset

    Returns:
        list of 0s and 1s
    """
    if pulses <= 0 or steps <= 0:
        return [0] * max(steps, 0)
    if pulses >= steps:
        return [1] * steps

    pattern: list[int] = []
    bucket = 0
    for _ in range(steps):
        bucket += pulses
        if bucket >= steps:
            bucket -= steps
            pattern.append(1)
        else:
            pattern.append(0)

    if offset > 0:
        pattern = pattern[-offset:] + pattern[:-offset]
    return pattern

# ─── MIDI Generation Functions ───────────────────────────────────────────

def generate_euclidean_groove(
    bpm: float = DEFAULT_BPM,
    bars: int = BARS_DEFAULT,
    swing_pct: float = 0.62,
    kick_pulses: int = 5,
    kick_steps: int = 16,
    humanize_ms: float = 12.0,
) -> MIDISequence:
    """
    Generate a full groove using Euclidean rhythms with micro-timing.

    Inspired by Daft Punk swing (62%) and Aphex Twin polyrhythms.

    Args:
        bpm: beats per minute
        bars: number of bars
        swing_pct: swing amount (0.5 = straight, 0.62 = Daft Punk, 0.66 = jazz)
        kick_pulses: Euclidean pulses for kick
        kick_steps: Euclidean steps for kick (per bar)
        humanize_ms: standard deviation for micro-timing randomization in ms
    """
    seq = MIDISequence(bpm=bpm)
    tick_per_16th = TICKS_PER_BEAT // 4  # 120 ticks

    # Swing offset (applies to off-beat 16th notes)
    swing_offset_ticks = int(tick_per_16th * (swing_pct - 0.5) * 2)

    # ─── Kick (Euclidean) ───
    kick_track = MIDITrack(name="kick")
    kick_pattern = euclidean_rhythm(kick_steps, kick_pulses)
    for bar in range(bars):
        bar_start = bar * BEATS_PER_BAR * TICKS_PER_BEAT
        for i, hit in enumerate(kick_pattern):
            if hit:
                micro = int(random.gauss(0, humanize_ms * TICKS_PER_BEAT / 1000))
                tick = bar_start + (i * tick_per_16th) + micro
                # Apply swing to off-beat positions
                if i % 2 == 1:
                    tick += swing_offset_ticks
                vel = random.randint(100, 127)
                kick_track.events.append(MIDIEvent(max(0, tick), "on", KICK, vel))
                kick_track.events.append(MIDIEvent(tick + 60, "off", KICK, 0))
    seq.tracks.append(kick_track)

    # ─── Snare (beats 2 and 4) ───
    snare_track = MIDITrack(name="snare")
    for bar in range(bars):
        bar_start = bar * BEATS_PER_BAR * TICKS_PER_BEAT
        for beat in [1, 3]:  # 0-indexed beats 2 and 4
            micro = random.choice([-20, 0, 15, 40])
            tick = bar_start + beat * TICKS_PER_BEAT + micro
            vel = random.randint(85, 115)
            note = SNARE if beat == 1 else CLAP
            snare_track.events.append(MIDIEvent(max(0, tick), "on", note, vel))
            snare_track.events.append(MIDIEvent(tick + 60, "off", note, 0))
    seq.tracks.append(snare_track)

    # ─── Hats (32nd notes with probability and sine drift) ───
    hat_track = MIDITrack(name="hats")
    tick_per_32nd = TICKS_PER_BEAT // 8  # 60 ticks
    for bar in range(bars):
        bar_start = bar * BEATS_PER_BAR * TICKS_PER_BEAT
        steps_per_bar = BEATS_PER_BAR * 8  # 32 steps
        for i in range(steps_per_bar):
            if random.random() > 0.55:  # ~45% hit probability
                drift = int(math.sin(i * 0.5) * 20)
                tick = bar_start + (i * tick_per_32nd) + drift
                vel = random.randint(30, 95)
                hat_track.events.append(MIDIEvent(max(0, tick), "on", CLOSED_HAT, vel))
                hat_track.events.append(MIDIEvent(tick + 25, "off", CLOSED_HAT, 0))
    seq.tracks.append(hat_track)

    # ─── Sub pulse (root note sustained) ───
    sub_track = MIDITrack(name="sub")
    for bar in range(bars):
        bar_start = bar * BEATS_PER_BAR * TICKS_PER_BEAT
        sub_track.events.append(MIDIEvent(bar_start, "on", SUB_NOTE, 60))
        sub_track.events.append(
            MIDIEvent(bar_start + int(TICKS_PER_BEAT * 3.8), "off", SUB_NOTE, 0)
        )
    seq.tracks.append(sub_track)

    # Sort all tracks
    for track in seq.tracks:
        track.sort()

    return seq

def generate_harmonic_sequence(
    key_root: int = 60,  # Middle C
    scale_type: str = "minor",
    bars: int = BARS_DEFAULT,
    bpm: float = DEFAULT_BPM,
    voicing: str = "triads",
) -> MIDISequence:
    """
    Generate a chord progression in the specified key.

    Args:
        key_root: MIDI note number for root (60 = C4)
        scale_type: "minor", "major", "dorian", "phrygian"
        bars: number of bars (one chord per bar)
        bpm: tempo
        voicing: "triads", "sevenths", "extended"
    """
    scales = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
        "phrygian": [0, 1, 3, 5, 7, 8, 10],
        "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    }

    intervals = scales.get(scale_type, scales["minor"])

    # Common progressions (scale degree indices, 0-based)
    progressions = [
        [0, 5, 3, 4],  # i - vi - iv - v
        [0, 3, 5, 4],  # i - iv - vi - v
        [0, 2, 5, 4],  # i - iii - vi - v
        [5, 3, 0, 4],  # vi - iv - i - v
    ]
    progression = random.choice(progressions)

    seq = MIDISequence(bpm=bpm)
    chord_track = MIDITrack(name="chords")
    bar_ticks = BEATS_PER_BAR * TICKS_PER_BEAT

    for bar in range(bars):
        degree = progression[bar % len(progression)]
        root = key_root + intervals[degree % len(intervals)]

        # Build chord voicing
        if voicing == "sevenths":
            notes = [root, root + 3, root + 7, root + 10]
        elif voicing == "extended":
            notes = [root, root + 3, root + 7, root + 10, root + 14]
        else:
            # Triads using scale intervals
            third = intervals[(degree + 2) % len(intervals)]
            fifth = intervals[(degree + 4) % len(intervals)]
            # Normalize relative to root
            note_third = key_root + third
            note_fifth = key_root + fifth
            while note_third <= root:
                note_third += 12
            while note_fifth <= root:
                note_fifth += 12
            notes = [root, note_third, note_fifth]

        tick_start = bar * bar_ticks
        tick_end = tick_start + int(bar_ticks * 0.95)  # Slight gap

        vel = random.randint(60, 85)
        for note in notes:
            chord_track.events.append(MIDIEvent(tick_start, "on", note, vel))
            chord_track.events.append(MIDIEvent(tick_end, "off", note, 0))

    chord_track.sort()
    seq.tracks.append(chord_track)
    return seq

def generate_texture_layer(
    bars: int = BARS_DEFAULT,
    bpm: float = DEFAULT_BPM,
    density: float = 0.3,
    note_range: tuple[int, int] = (48, 84),
) -> MIDISequence:
    """
    Generate an atmospheric texture layer with sparse, evolving notes.

    Creates drone-like MIDI patterns for pads, granular textures, or ambience.

    Args:
        bars: number of bars
        bpm: tempo
        density: probability of a note event per 8th note position (0.0–1.0)
        note_range: (low_note, high_note) MIDI range
    """
    seq = MIDISequence(bpm=bpm)
    texture_track = MIDITrack(name="texture")
    tick_per_8th = TICKS_PER_BEAT // 2  # 240 ticks

    for bar in range(bars):
        bar_start = bar * BEATS_PER_BAR * TICKS_PER_BEAT
        steps_per_bar = BEATS_PER_BAR * 2  # 8th notes
        for i in range(steps_per_bar):
            if random.random() < density:
                note = random.randint(note_range[0], note_range[1])
                tick = bar_start + (i * tick_per_8th) + random.randint(-10, 10)
                vel = random.randint(25, 70)
                # Long sustain for drone feel
                duration = random.randint(
                    TICKS_PER_BEAT, TICKS_PER_BEAT * 3
                )
                texture_track.events.append(
                    MIDIEvent(max(0, tick), "on", note, vel)
                )
                texture_track.events.append(
                    MIDIEvent(tick + duration, "off", note, 0)
                )

    texture_track.sort()
    seq.tracks.append(texture_track)
    return seq

# ─── WAV Synthesis (Pure Python / NumPy) ─────────────────────────────────

def render_sequence_to_wav(
    sequence: MIDISequence,
    output_path: str,
    sr: int = DEFAULT_SR,
) -> str:
    """
    Render a MIDISequence to a WAV file using pure-Python synthesis.

    Drums are synthesized with dedicated drum synths.
    Melodic notes use sine waves with envelope.

    Args:
        sequence: the MIDI sequence to render
        output_path: filesystem path for the output WAV
        sr: sample rate

    Returns:
        absolute path to the rendered WAV file
    """
    import scipy.io.wavfile as wavfile

    # Calculate total duration
    total_ticks = sequence.total_ticks + TICKS_PER_BEAT  # Buffer
    total_samples = int(total_ticks * sequence.tick_duration_s * sr) + sr  # +1s buffer
    audio = np.zeros(total_samples, dtype=np.float64)

    drum_notes = {KICK, SNARE, CLAP, CLOSED_HAT, OPEN_HAT}

    for track in sequence.tracks:
        for event in track.events:
            if event.event_type != "on" or event.velocity == 0:
                continue

            sample_pos = int(event.tick * sequence.tick_duration_s * sr)
            if sample_pos >= total_samples:
                continue

            vel_scale = event.velocity / 127.0

            if event.note in drum_notes:
                # Drum synthesis
                if event.note == KICK:
                    wave = _synth_kick(sr)
                elif event.note in (SNARE, CLAP):
                    wave = _synth_snare(sr)
                elif event.note in (CLOSED_HAT, OPEN_HAT):
                    wave = _synth_hihat(sr)
                else:
                    continue
            else:
                # Find note-off to determine duration
                dur_ticks = TICKS_PER_BEAT  # Default 1 beat
                for off_evt in track.events:
                    if (
                        off_evt.event_type == "off"
                        and off_evt.note == event.note
                        and off_evt.tick > event.tick
                    ):
                        dur_ticks = off_evt.tick - event.tick
                        break

                dur_s = dur_ticks * sequence.tick_duration_s
                freq = _note_to_freq(event.note)

                if event.note < 36:
                    # Sub-bass: pure sine
                    wave = _synth_sine(freq, dur_s, sr) * SUB_AMPLITUDE
                else:
                    # Melodic: sine with gentle attack/release
                    wave = _synth_sine(freq, dur_s, sr) * 0.3
                    # Apply fade in/out
                    fade_len = min(FADE_SAMPLES, len(wave) // 4)
                    if fade_len > 0:
                        fade_in = np.linspace(0, 1, fade_len)
                        fade_out = np.linspace(1, 0, fade_len)
                        wave[:fade_len] *= fade_in
                        wave[-fade_len:] *= fade_out

            # Mix into output buffer
            wave *= vel_scale
            end_pos = min(sample_pos + len(wave), total_samples)
            segment_len = end_pos - sample_pos
            audio[sample_pos:end_pos] += wave[:segment_len]

    # Normalize to prevent clipping
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.95

    # Write WAV (16-bit PCM)
    audio_int16 = (audio * 32767).astype(np.int16)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    wavfile.write(output_path, sr, audio_int16)

    logger.info("Rendered WAV: %s (%.1fs, %d samples)", output_path, len(audio) / sr, len(audio))
    return os.path.abspath(output_path)

def save_sequence_as_midi(sequence: MIDISequence, output_path: str) -> str:
    """
    Save a MIDISequence as a standard MIDI file using mido.

    Args:
        sequence: the MIDI sequence to save
        output_path: filesystem path for the output .mid file

    Returns:
        absolute path to the saved MIDI file
    """
    try:
        import mido
    except ImportError:
        logger.error("mido not installed. Cannot save MIDI files. pip install mido")
        raise

    mid = mido.MidiFile(ticks_per_beat=sequence.ticks_per_beat)

    # Master tempo track
    master = mido.MidiTrack()
    mid.tracks.append(master)
    master.append(
        mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(sequence.bpm), time=0)
    )

    for track in sequence.tracks:
        midi_track = mido.MidiTrack()
        mid.tracks.append(midi_track)

        # Convert absolute ticks to delta
        last_tick = 0
        for event in track.events:
            delta = max(0, event.tick - last_tick)
            msg_type = "note_on" if event.event_type == "on" else "note_off"
            midi_track.append(
                mido.Message(
                    msg_type,
                    note=event.note,
                    velocity=event.velocity,
                    time=delta,
                    channel=event.channel,
                )
            )
            last_tick = event.tick

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    mid.save(output_path)
    logger.info("Saved MIDI: %s", output_path)
    return os.path.abspath(output_path)
