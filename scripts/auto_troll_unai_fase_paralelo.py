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

print("🔥 CORTEX // FASE PARALELA (5s) — CLICK EN IG")
time.sleep(5)

MESSAGES = [
    "Por cierto Unai Bellamy, ahora que estás asimilando el trauma...",
    "He puesto a la IA a componerte un himno de techno industrial sobre tu obsolescencia analógica.",
    "Literalmente lo estoy generando en background mientras te escribo esto.",
    "Se llama 'Unai The Analog Ghost'.",
    "Prepárate."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(1.2)

print("✅ FASE PARALELA ENVIADA.")
