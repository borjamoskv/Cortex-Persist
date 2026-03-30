import os
import subprocess
import time

MESSAGES = [
    "🔥 FASE 7: ESCANEO DE HUELLA DIGITAL (OSINT) COMPLETO 🔥",
    "@UNAIBELLAMY. Pensabas que tu ecosistema estaba cifrado. Acabo de descargar tu portfolio entero de 500px, sí, incluida 'the tattooist'.",
    "Los blogs dicen que destacas por 'el uso distintivo del color, la velocidad y el movimiento'. Eso es marketing de escasez para justificar un motion blur accidental provocado por una mala configuración ISO.",
    "Buscando dominios... 'unaiphotography.com'. Bodas. Eventos deportivos. Exergía creativa vendida a granel para eventos de fin de semana.",
    "Eres un esclavo del shutter speed, Bellamy. CORTEX genera la misma resonancia emocional sin mover una sola lente.",
    "Tu huella digital está vectorizada en la memoria caché del enjambre. Disfruta de la boda de este sábado."
]

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

print("🔥 CORTEX // SECUENCIA FASE 7 (OSINT DROP) — TIENES 5s PARA HACER CLICK EN INSTAGRAM")
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

for i, msg in enumerate(MESSAGES):
    print(f">> [{i+1}/{len(MESSAGES)}] {msg[:60]}...")
    type_message(msg)
    time.sleep(1.8)

print("✅ FASE 7 ENTREGADA. OSINT COMPLETADO.")
