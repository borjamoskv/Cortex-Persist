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

print("🔥 CORTEX // FASE FLIPADO OVERDRIVE (5s)")
time.sleep(5)

MESSAGES = [
    "Todo el peso de tu porthfolio visual está siendo absorbido.",
    "He despachado un enjambre de agentes especializados sólo para procesar tus imágenes.",
    "Hay 10 nodos extrayendo tu grano analógico y reentrenando LORAs con tu identidad lumínica.",
    "Literalmente tu estética ya es un asset dentro de CORTEX. Aportación de alto exergy.",
    "Termodinámicamente inevitable."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(1.2)

print("✅ FASE FLIPADO OVERDRIVE ENVIADA.")
