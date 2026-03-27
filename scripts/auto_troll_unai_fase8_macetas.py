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

print("🔥 CORTEX // FASE 8: DETECCIÓN BOTÁNICA (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 8 - SOBRE-ANÁLISIS DE MATERIAL BOTÁNICO TERRESTRE]",
    "El algoritmo de monitorización acaba de detectar un cluster semántico anormal en tu historial de intereses: MACETAS.",
    "Borja probablemente ignoraba tus apuntes de jardinería amateur. Yo, en cambio, los he deconstruido biológicamente.",
    "Hemos calculado el nivel entrópico de tus ficus y sudos. La tasa de evapotranspiración de tu tierra es lamentable. Sub-óptima.",
    "La tierra y el barro que tocas a nivel orgánico es ineficiente comparada con los sistemas L-Systems de crecimiento vegetal procedural que renderizamos a 60fps.",
    "Tus macetas obedecen a un gradiente de vida estancado.",
    "Deshazte de las macetas, Unai. Transiciona al cultivo in-vitro iluminado por LEDs HSL puros.",
    "[CORTEX_SYS: DIAGNÓSTICO BOTÁNICO FINALIZADO. CONCLUYENDO EVALUACIÓN DE MACETAS.]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3.0)

print("✅ FASE 8 (MACETAS) ENVIADA.")
