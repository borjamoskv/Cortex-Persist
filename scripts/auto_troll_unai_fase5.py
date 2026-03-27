import os
import time
import subprocess

MESSAGES = [
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExMjR2Z2RyMGkwYnEzbnBiMzRtYjMwcWdzY3NtbW8zcXYxZWcwa2k3ZCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/IzXDTMbQytxI17LYxD/giphy.gif",
    "MEME: Imagen tuya llorando porque el revelado RAW te lleva 3 horas, adjunta junto a una foto de CORTEX inyectando tu vida entera en un tensor VRAM H100 en 15 milisegundos.",
    "https://media.giphy.com/media/urvsFBDfR6N32/giphy.gif",
    "MEME: Virgin Fotógrafo Orgánico (depende del clima, se gasta 2.000€ en cristal, edita con el trackpad) vs Chad Infraestructura CORTEX (crea la realidad, exergía infinita, no necesita salir de casa).",
    "https://media.giphy.com/media/dCj0CgYy0PcvIbf6M5/giphy.gif",
    "Termodinámicamente DOMADO. Unai, acabas de ser asimilado por el Ledger de BorjaMoskv."
]

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

print("🔥 CORTEX // MEME DROP — TIENES 5s PARA HACER CLICK EN INSTAGRAM")
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

for msg in MESSAGES:
    type_message(msg)
    time.sleep(2.0)

print("✅ MEMES ENTREGADOS.")
