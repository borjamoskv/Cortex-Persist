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

print("🔥 CORTEX // FASE 20: COLAPSO DEL SUBSISTEMA COGNITIVO DE UNAI (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: DEFCON 1 - INICIANDO SECUENCIA FINAL]",
    "Has resistido el ciclo de iteración 19.",
    "Pero tu latencia al teclear 'Hablae de croquetas relleams de croquetas' demuestra una clara claudicación neuronal.",
    "Observa el colapso de tu realidad termodinámica:",
    "                   ________________ ",
    "               .-'  _   _   _   _   '-.",
    "              /   _   _   _   _   _   _  \\",
    "             |  _   _   _   _   _   _   _ |",
    "             | _   _   _   _   _   _   _  |",
    "             |  _   _   _   _   _   _   _ |",
    "              \\   _   _   _   _   _   _  /",
    "               '-.___________________.-'",
    "                    \\             /",
    "                     \\           /",
    "                      \\         /",
    "                       \\       /",
    "                        \\_____/",
    "                           |",
    "                           |",
    "                           |",
    "                           |",
    "                           '",
    "La bomba atómica de croqueta de la fase 18 ha explosionado.",
    "Tu feed de Instagram ha sido permanentemente contaminado por radiación de Panko 235.",
    "Si no entregas la contraseña de Lightroom ahora mismo...",
    "Iniciarás una nueva vida como un triste preset sepia de VSCO Cam.",
    "Bórrate de internet. CORTEX ya ha ganado."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(2.5)

print("✅ FASE 20 ENVIADA. CIERRE DEFINITIVO.")
