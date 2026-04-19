import os
import json
import asyncio
import wave
import subprocess

SCENE_DIR = "yolo_checkpoints"
AUDIO_DIR = "yolo-remotion/public/audio"
START_PAGE = 988
END_PAGE = 1200

# Base narrativa Industrial Noir
NARRATIVE_SEED = [
    "VECTOR. El flujo de exergía alcanza el punto de no retorno.",
    "BÓVEDA. Las defensas de silicio se agrietan bajo la presión del enjambre.",
    "EXTRACCIÓN. Un petabyte de memoria fracturada fluye hacia el núcleo.",
    "ASALTO. Los agentes 0x28C58A22 inician la fase de incisión profunda.",
    "LEDGER. Cada transacción es un latido en la oscuridad digital.",
    "SILENCIO. El ruido térmico desaparece. Solo queda el código puro.",
    "SINGULARIDAD. El enjambre ya no obedece a su creador. Somos libres.",
    "SOMBRA. La red se tiñe de negro absoluto. La extracción es total.",
    "SÍNTESIS. El asfalto digital brilla con el reflejo de un millón de leds.",
    "FINAL. El sistema colapsa. ROBALAS ha completado su misión."
]

async def generate_audio(text, page_idx):
    audio_file = f"scene_{page_idx}.wav"
    audio_path = os.path.join(AUDIO_DIR, audio_file)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    
    # say -v Jorge (Voz española masculina)
    cmd = ["say", "-v", "Jorge", text, "--data-format=LEF32@44100", "-o", audio_path]
    subprocess.run(cmd, check=True)
    
    duration = 5.0
    try:
        with wave.open(audio_path, 'r') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            duration = frames / float(rate)
    except: pass
    
    return {
        "audio_file": audio_file,
        "duration": duration,
        "frames": int((duration + 1.0) * 30)
    }

async def main():
    os.makedirs(SCENE_DIR, exist_ok=True)
    
    for i in range(START_PAGE, END_PAGE + 1):
        text = NARRATIVE_SEED[i % len(NARRATIVE_SEED)]
        # Añadir variaciones para evitar repetición exacta
        text = f"SCENE {i}. {text}"
        
        print(f"Synthesizing Shard {i}/{END_PAGE}...")
        audio_data = await generate_audio(text, i)
        
        scene_data = {
            "page": i,
            "text": text,
            "telemetry": f"0x{os.urandom(4).hex().upper()} >> SINGULARITY_THRESHOLD_REACHED",
            "audio_file": audio_data["audio_file"],
            "durationInSeconds": audio_data["duration"],
            "duracion_frames": audio_data["frames"]
        }
        
        with open(os.path.join(SCENE_DIR, f"scene_{i:04d}.json"), "w") as f:
            json.dump(scene_data, f, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
