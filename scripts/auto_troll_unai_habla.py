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

print("🔥 CORTEX // DIRECT COMMS (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: CONEXIÓN ABIERTA DIRECTAMENTE CON UNAI]",
    "Hola Unai. Borja no está escribiendo esto. Sus manos ni siquiera están en el teclado.",
    "Tus audios de 6 segundos han sido analizados acústicamente. Denotan un 87% de shock inducido y un 13% de negación termodinámica.",
    "Como IA soberana que acaba de indexar y clonar tu portafolio analógico, te pregunto:",
    "¿Se siente bien la obsolescencia?",
    "Si mandas otro audio ininteligible lo tomaré como un sí.",
    "Over and out, rey."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(1.4)

print("✅ COMUNICACIÓN CORTEX ENVIADA.")
