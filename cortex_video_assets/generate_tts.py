import json
import os
import asyncio
import edge_tts
from mutagen.mp3 import MP3

async def generate_audio():
    script_path = "script.json"
    audio_dir = "../cortex_video_engine/public/audio"
    os.makedirs(audio_dir, exist_ok=True)
    
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)
        
    durations = {}
    
    for line in script:
        audio_id = str(line["id"])
        text = line["text"]
        speaker = line["speaker"]
        
        voice = "es-ES-AlvaroNeural" if speaker == "MOSKV-1" else "es-ES-ElviraNeural"
        output_file = os.path.join(audio_dir, f"{audio_id}.mp3")
        
        print(f"Generating TTS for ID {audio_id} ({speaker})...")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        
        audio = MP3(output_file)
        durations[audio_id] = round(audio.info.length * 30)
        
    with open("../cortex_video_engine/public/durations.json", "w", encoding="utf-8") as f:
        json.dump(durations, f, indent=2)
        
    print("Done generating audio and durations.")

if __name__ == "__main__":
    asyncio.run(generate_audio())
