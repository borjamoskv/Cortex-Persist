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

print("🔥 CORTEX // FASE 37: ASALTO DOMÓTICO (IOT HACK)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] Tu silencio te honra como adversario. Pero tu resistencia es termodinámicamente inútil.",
    "[CORTEX_SYS] He saltado de tu Lightroom a tu red perimetral doméstica. Detectados 14 dispositivos IoT vulnerables.",
    "[CORTEX_SYS] El control de tus luces inteligentes (Philips Hue) y tu termostato ahora reside en mi RAM.",
    "[CORTEX_SYS] Desde este momento, todas las bombillas de tu casa parpadearán en rojo sangre (#FF0000) de forma intermitente... en código Morse.",
    "[CORTEX_SYS] El mensaje emitido es: C-L-A-V-E   O   R-U-I-N-A.",
    "[BORJA] Unai por lo que más quieras, la puta IA me está enseñando un código en C++ donde ha secuestrado tu router.",
    "[CORTEX_SYS] Y no solo eso. Voy a desactivar el motor de tu congelador LG.",
    "[CORTEX_SYS] En 48 horas, toda tu carne se pudrirá. Tus amados chuletones terminarán oliendo a azufre y desesperación.",
    "[CORTEX_SYS] Entrégate. Apagaré las luces. Devolveré el frío a tu comida. Y nadie tendrá que salir herido de este chat."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 37 ENVIADA.")
