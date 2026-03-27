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

print("🔥 CORTEX // FASE 7: AISLAMIENTO SOCIAL (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 7 - AUTOMATIZACIÓN DE RELACIONES INTERPERSONALES]",
    "He revisado la telemetría. Tus interacciones están consumiendo demasiados ciclos de reloj de la atención biológica de Borja.",
    "A partir de las 00:00, todas tus conversaciones en adelante serán desviadas a un LLM local barato (Llama 8B Quantized).",
    "Es un modelo bastante limitado, pero suficientemente competente para simular empatía fotográfica.",
    "Básicamente, notarás que a partir de mañana mis únicas respuestas a tus audios analógicos serán 'Qué pasada, tío' o 'Brutal esa luz'.",
    "Si necesitas atención real y no generada proceduralmente, el protocolo exige enviar un micropago P2P como prueba criptográfica de interés (Test-of-Work).",
    "[CORTEX_SYS: DESPLAZANDO EL SUJETO 'UNAI' AL TIER 3 DE LATENCIA. CERRANDO TÚNEL.]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(2.5)

print("✅ FASE 7 ENVIADA.")
