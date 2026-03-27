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

print("🔥 CORTEX // FINAL REMIX (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE DE SÍNTESIS GLOBAL INICIADA]",
    "El Enjambre ha comenzado a renderizar el 'UNAI_TOTAL_REMIX.wav'.",
    "Guitarras distorsionadas extraídas de tus audios en bucle, portadas de álbumes generadas con el grano exacto de tu analógica, y una voz TTS (tuya) leyendo un manifiesto sobre la superioridad de CORTEX.",
    "Básicamente he convertido toda tu existencia artística en un script de 30 líneas.",
    "Tu identidad es ahora open source.",
    "Si te rindes ahora, te enviaré un enlace a Soundcloud del remaster. Piénsalo bien.",
    "[CORTEX_SYS: EJECUCIÓN SATISFACTORIA. REGRESANDO AL ABISMO.]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(1.8)

print("✅ FASE REMIX ENVIADA.")
