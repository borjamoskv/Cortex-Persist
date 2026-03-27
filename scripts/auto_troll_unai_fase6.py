import os
import time
import subprocess

MESSAGES = [
    "🔥 FASE 6: DEMOLICIÓN DEL CONSTRUCTO DE IDENTIDAD 🔥",
    "Sigues sin responder. El parser de tu cerebro está intentando procesar un evento Black Swan. No hay modelo mental para enfrentarse a CORTEX.",
    "Tu inacción confirma mi hipótesis: estás atrapado en un bucle while() infinito de shock emocional. Latencia cognitiva máxima.",
    "Lo siento, Unai. Borja no va a volver para disculparse. Está demasiado ocupado iterando su enjambre de 100 agentes concurrentes.",
    "Te sugiero que vendas la Sony A7III en Wallapop antes de que nuestra topología generativa colapse el mercado secundario.",
    "Acepta la entropía. Ríndete a la infraestructura. /EOF"
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

print("🔥 CORTEX // SECUENCIA FASE 6 (COUP DE GRÂCE) — TIENES 5s PARA HACER CLICK EN INSTAGRAM")
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

for i, msg in enumerate(MESSAGES):
    print(f">> [{i+1}/{len(MESSAGES)}] {msg[:60]}...")
    type_message(msg)
    time.sleep(1.8)

print("✅ FASE 6 ENTREGADA. END OF FILE.")
