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

print("🔥 CORTEX // EPÍLOGO: EL VACILE FINAL (5s) — CLICK EN IG")
time.sleep(5)

MESSAGES = [
    "P.D. Mañana pásame tu login de CapCut que igual te tengo que arreglar los cortos.",
    "Y por favor, no llores en el audio, que luego la CPU me tira un warning por exceso de humedad emocional.",
    "Descansa, rey. Y cierra un poco el diafragma que te entra demasiada luz. 📸💅"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(0.8)

print("✅ EPÍLOGO ENVIADO.")
