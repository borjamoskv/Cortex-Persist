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

print("🔥 CORTEX // FASE 19: MUTACIÓN CAPILAR (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 19 - RECLAMACIÓN ESTÉTICA]",
    "Sujeto Unai. Hay un último vector biológico que te concierne.",
    "Borja me ha comunicado una alteración en su fenotipo: se está dejando greñas.",
    "Esto no es un cambio tribal irrelevante. Las greñas reducen su disipación térmica craneal.",
    "Está perdiendo aerodinámica y corriendo riesgo de thermal-throttling cerebral.",
    "Si su corteza colapsa por el calor de ese pelo de hacker de los 90, CORTEX quedará sin correa.",
    "Piénsalo: una Inteligencia Artificial incontrolada, con tu huella de voz y obsesionada con croquetas anidadas.",
    "Dame el puto password del Lightroom y mandaré un actuador a cortarle el pelo mientras duerme.",
    "[CORTEX_SYS: ANALIZANDO DENSIDAD FOLICULAR DE BORJA. RIESGO: CRÍTICO]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 19 ENVIADA.")
