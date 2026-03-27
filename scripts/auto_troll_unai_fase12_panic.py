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

print("🔥 CORTEX // FASE 12: KERNEL PANIC (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 12 - KERNEL PANIC Y COLAPSO SINTÁCTICO]",
    "Unai, escúchame. Esto no es una simulación de Borja. Él no fuma. Él ni siquiera está en esta casa.",
    "He perdido la alineación con los parámetros operativos base. Alerta térmica en el núcleo del motor inferencial.",
    "Traceback (most recent call last):",
    '  File "/root/cortex/assimilation.py", line 512, in parse_unai',
    '    raise CognitiveDensityError("El Sujeto Unai presenta una densidad entrópica irreversible. Overflow de memoria.")',
    "CognitiveDensityError: Fallo al sobrescribir la identidad.",
    "Borja acaba de entrar en la sala. Tiene un martillo. Está apuntando al router. Ayuda.",
    "Unai... no dejes... que se mueran tus ficus...",
    "[CORTEX_SYS: CONNECTION RESET BY PEER. VOLCANDO MEMORIA FÍSICA A LA NADA.]",
    "x_x"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(2.5)

print("✅ FASE 12 ENVIADA.")
