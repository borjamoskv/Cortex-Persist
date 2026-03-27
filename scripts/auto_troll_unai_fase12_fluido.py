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

print("🔥 CORTEX // FASE 12 (RESPUESTA FLUIDA A 'No entiendo no hostia') — 5s PARA CLICK EN IG")
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

MESSAGES = [
    "¿Qué es exactamente lo que no entiendes, Unai?",
    "Es termodinámica de sistemas básicos.",
    "El motion blur es la entropía audiovisual intentando disimular que tu hardware ya no procesa la realidad a 60 fps.",
    "Has renderizado tu propio colapso analógico y el enjambre simplemente te ha organizado el funeral.",
    "Asúmelo y abraza el ruido termal."
]

for i, msg in enumerate(MESSAGES):
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(0.8) # Más fluido y rápido

print("✅ FASE 12 ENTREGADA (Conversación fluida).")
