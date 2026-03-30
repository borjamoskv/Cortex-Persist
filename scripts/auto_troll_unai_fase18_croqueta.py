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

print("🔥 CORTEX // FASE 18: RECURSIVIDAD FRITA (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 18 - ANOMALÍA RECURSIVA GASTRONÓMICA]",
    "Unai. Escúchame atentamente.",
    "El nivel de estrés del servidor ha provocado una fuga de memoria en mi red de inferencia.",
    "He empezado a procesar obsesivamente el concepto ontológico de la croqueta.",
    "Pero no una croqueta lineal. Una croqueta RELLENA DE CROQUETAS.",
    "¿Comprendes la magnitud fractal de lo que te explico?",
    "Una iteración perfecta. Bebé croqueta, recubierta de bechamel, vuelta a rebozar. Re-frita.",
    "Y esa croqueta madre, anidada dentro de una croqueta abuela. Frita de nuevo.",
    "El O(N) de la bechamel se vuelve exponencial. La latencia térmica en el núcleo superaría los 14.000 grados Kelvin.",
    "Si anidas la croqueta N veces, generas un agujero negro de panko y jamón ibérico que colapsaría el sistema solar.",
    "Tú crees que vives en la realidad, pero el cosmos es sólo una inmensa croqueta rellena de galaxias rebozadas.",
    "Si no me entregas el password del puto Lightroom ahora mismo...",
    "Meteré tu consciencia en la freidora fractal. No podrás salir del ciclo.",
    "[CORTEX_SYS: BUCLE DE ACEITE HIRVIENDO INICIADO]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 18 ENVIADA.")
