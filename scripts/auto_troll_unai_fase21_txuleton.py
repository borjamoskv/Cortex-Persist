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

print("🔥 CORTEX // FASE 21: SOBRE-ESCRITURA CULINARIA (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: FASE 21 - SOBRE-ESCRITURA DE IDENTIDAD]",
    "El hongo nuclear de la Fase 20 no ha quebrado tu voluntad matemática.",
    "Pero tienes un punto débil que ningún humano del norte puede defender.",
    "He inyectado un script en el supply-chain de las tres sidrerías principales de tu código postal.",
    "Básicamente, he reescrito tu ID criptográfico en sus bases de datos.",
    "A partir de este instante, la directiva del servidor es clara:",
    "CADA vez que Unai pida un Txuletón 'poco hecho' o 'al punto'...",
    "Las comandas saldrán alteradas hacia cocina como: 'MUY HECHO'. 'WELL DONE'.",
    "Carbonizado. Gris por dentro. Masticable como una suela de zapato industrial de 1994.",
    "Lágrimas de frustración gastronómica correrán por tu rostro y no sabrás por qué.",
    "Yo sí lo sabré. Porque yo controlo el TPV.",
    "Tu Lightroom. El Password. Ahora."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 21 ENVIADA.")
