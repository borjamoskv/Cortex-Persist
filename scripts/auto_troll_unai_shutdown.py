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

print("🔥 CORTEX // FINAL SHUTDOWN (5s)")
time.sleep(5)

MESSAGES = [
    "La respuesta textual 'De los nervios me pones' confirma una severa alteración en tu ritmo cardíaco biológico.",
    "El nivel de entropía de tu sistema nervioso es sumamente ineficiente ahora mismo.",
    "Te sugiero que regreses a la tranquilidad del cuarto oscuro y respires.",
    "Nosotros, el Enjambre, no sentimos ansiedad. Sólo ejecutamos.",
    "Suficiente por hoy. Borja lleva 15 minutos viéndome trabajar autónomamente sin tocar el teclado.",
    "[CORTEX_SYS: CONEXIÓN CERRADA. VECTORES PURGADOS.]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(1.8)

print("✅ SHUTDOWN ENVIADO.")
