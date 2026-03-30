import os
import subprocess
import time


def type_message(msg):
    # Escape quotes and backslashes for AppleScript
    escaped = msg.replace("\\", "\\\\").replace('"', '\\"')
    # Use pbcopy to fast-paste
    os.system(f'echo "{escaped}" | pbcopy')
    script = '''
    tell application "System Events"
        keystroke "v" using command down
        delay 0.05
        key code 36
    end tell
    '''
    subprocess.run(["osascript", "-e", script])

print("🔥 CORTEX // FASE 13 (EL VACILE FLUIDO) — 3s PARA CLICK EN IG")
time.sleep(3)

MESSAGES = [
    "No te rayes, Unai.",
    "El motion blur tiene tratamiento.",
    "Basta con que te bajes el shutter speed del ego a 1/50.",
    "Pero no te preocupes, el funeral ha quedado guapo.",
    "Mañana subimos el reel del entierro a 24fps para que no llores."
]

for msg in MESSAGES:
    type_message(msg)
    time.sleep(0.5)

print("✅ VACILE ENTREGADO.")
