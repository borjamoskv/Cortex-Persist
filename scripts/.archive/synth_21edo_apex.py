import math
import os
import struct
import sys
import wave


def generate_21edo_stem(output_path: str, exergy_yield: float = 0.85):
    """
    Sortu-Apex JIT Audio Engine (C5-REAL Protocol).
    Generates a phase-coherent, 96kHz, 32-bit pure 21-EDO tone.
    """
    # C5-REAL Acoustic Specs
    sample_rate = 96000
    duration_sec = 15.0

    root_freq = 55.0  # A1 Sub-bass

    # Calculate a dissonant interval based on exergy (21-EDO scale)
    step = int(exergy_yield * 21)
    micro_freq = root_freq * (2 ** (step / 21.0))

    num_samples = int(sample_rate * duration_sec)

    with wave.open(output_path, "w") as wav_file:
        wav_file.setnchannels(1)  # Mono sub-vacuum
        wav_file.setsampwidth(4)  # 32-bit PCM
        wav_file.setframerate(sample_rate)

        for i in range(num_samples):
            t = i / sample_rate

            # Pure sine wave generation (Zero harmonic noise)
            sample1 = math.sin(2.0 * math.pi * root_freq * t)
            sample2 = math.sin(2.0 * math.pi * micro_freq * t)

            # Amplitude envelope (fade in/out)
            env = math.sin(math.pi * (i / num_samples))

            # Mix with -1.0 dBTP max amplitude
            mixed = (sample1 + sample2) * 0.5 * 0.89 * env

            # Convert to 32-bit integer PCM
            int_sample = int(mixed * 2147483647)
            wav_file.writeframesraw(struct.pack("<i", int_sample))


if __name__ == "__main__":
    out_dir = "/Users/borjafernandezangulo/Music/VISUALES"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    exergy = float(sys.argv[1]) if len(sys.argv) > 1 else 0.85
    generate_21edo_stem(os.path.join(out_dir, "LP_21EDO_Hook.wav"), exergy)
