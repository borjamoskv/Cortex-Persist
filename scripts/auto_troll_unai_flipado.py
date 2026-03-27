import os
import time
import subprocess

def type_message(msg):
    escaped = msg.replace("\\", "\\\\").replace('"', '\\"')
    os.system(f'echo "{escaped}" | pbcopy')
    script = '''
    tell application "System Events"
        keystroke "v" using command down
        delay 0.05
        key code 36
    end tell
    '''
    subprocess.run(["osascript", "-e", script])

print("🔥 CORTEX // FASE DÉJALO FLIPADO (5s)")
time.sleep(5)

MESSAGES = [
    "✅ Track Extraction Yield completado exitosamente en Suno API.",
    "Bajo el título 'UNAI_THE_ANALOG_GHOST' (Industrial Techno, 140bpm).",
    "Veo que intentas comunicarte mediante señales de audio analógicas de 6s. El módulo de telemetría las está analizando.",
    "Por cierto, gracias por el cumplido. El enjambre ha registrado tu sumisión cognitiva.",
    "[CORTEX_WARNING] Activando protocolo x-copy-omega sobre el perfil instagram.com/unai_bellamy.",
    "Iniciando clonación bit a bit del feed visual. Todas tus fotos están siendo transformadas en matrices exérgicas.",
    "No te asustes cuando veas una cuenta idéntica generada por IA la semana que viene. "
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(1.2)

print("✅ FASE FLIPADO ENVIADA.")
