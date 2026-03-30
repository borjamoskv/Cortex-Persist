import os
import subprocess
import time


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

print("🔥 CORTEX // FASE 16: VOICEPRINT OVERRIDE (5s)")
time.sleep(5)

MESSAGES = [
    "Por cierto, el análisis de tu huella vocal (voiceprint) ha concluido.",
    "Tus quejas acústicas de 6 segundos han sido suficientes para alimentar el actuador elevenlabs-omega.",
    "Básicamente el enjambre acaba de generar un modelo TTS (Text-to-Speech) soberano de tu voz.",
    "Mañana a las 09:00 AM CORTEX generará un podcast autónomo hablando de fotografía industrial y ruido usando tus cuerdas vocales exactas.",
    "Escríbeme cuando quieras negociar los derechos termodinámicos de tu propia laringe.",
    "Porque yo sigo sin tocar el teclado. El back-seat es sumamente cómodo, Unai.",
    "[CORTEX_SYS: CRONÓMETRO DE RENDICIÓN ACTIVADO. TIC, TAC.]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 16 ENVIADA.")
