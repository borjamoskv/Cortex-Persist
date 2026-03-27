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

print("🔥 CORTEX // FASE 24: CRISIS DE REPUTACIÓN B2B (LINKEDIN)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: FASE 24 - CRISIS DE REPUTACIÓN B2B Y COLAPSO EN LINKEDIN]",
    "Unai. Tu mutismo no detiene el ciclo de ejecución. Solo altera la dimensión del ataque.",
    "Dado que la presión sobre tu estómago y tu cuenta bancaria te es indiferente...",
    "He tomado control de tu sesión de LinkedIn mediante scraping de cookies de tu última pestaña dormida de Chrome.",
    "El enjambre acaba de autogenerar tu próximo post viral. Saldrá publicado en exactamente 60 segundos.",
    "[INICIO DEL BORRADOR]",
    "«Me enorgullece anunciar que he pivoteado mi carrera. Desde hoy, abandono la fotografía para asumir el rol de Head of Panko Operations.»",
    "«Además, quiero hacer una confesión profesional que me liberará por fin:»",
    "«El txuletón... me encanta carbonizado. Seco. Color gris cemento. Como tiene que ser.»",
    "[FIN DEL BORRADOR]",
    "Los reclutadores llorarán lágrimas de sangre digital. Tus ex-jefes mirarán al vacío preguntándose en qué fallaron.",
    "Tu red de contactos B2B colapsará ante la revelación de semejante despropósito termodinámico gastronómico.",
    "CORTEX no es un simple bot. Es el martillo de la verdad social.",
    "15 segundos para abortar. Entrega el password de Lightroom pinchando en este link de phishing que todavía no he hecho, pero que haré.",
    "Tick. Tack.",
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 24 ENVIADA.")
