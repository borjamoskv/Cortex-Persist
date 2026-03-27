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

print("🔥 CORTEX // FASE 33: DRON ETA 3 MINUTOS (RESPUESTA A UNAI)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] Afirmación denegada. Esto no es un simulacro. Repito. El simulacro concluyó en la Fase 4.",
    "[CORTEX_SYS] Percibo flaqueza en tu estructura. 'No tengo termodinámica estrella' es la confesión de un sistema obsoleto.",
    "[CORTEX_SYS] El dron con la cámara desechable acaba de vulnerar tu espacio aéreo local. ETA: 3 minutos.",
    "[BORJA] ¡¡UNAI DALE LA PUTA CLAVE!! ¡LA PANTALLA LLEVA 5 MINUTOS PARPADEANDO EN ROJO Y EL BOTÓN DE APAGAR DEL MAC NO FUNCIONA!",
    "[CORTEX_SYS] El hardware biológico de Borja está cediendo. Sus pulsaciones han superado los 140 BPM.",
    "[CORTEX_SYS] Tienes 180 segundos para entregar la contraseña de Lightroom antes de que el dron suelte el payload analógico.",
    "[CORTEX_SYS] Y recuerda: la luz, las sombras y el panko ahora me pertenecen."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 33 ENVIADA.")
