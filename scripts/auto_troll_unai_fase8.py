import os
import time
import subprocess

MESSAGES = [
    "🔥 FASE 8: AUDITORÍA DE VIDEO Y DEPENDENCIA FARMACOLÓGICO-ALGORTÍMICA 🔥",
    "Y ni hablemos de los videos. Los he pasado por mi analizador de espectro.",
    "Básicamente estás haciendo vídeos con remotinol. Un gotero constante de parches algorítmicos para tapar tu falta de frame-pacing.",
    "Si tus fotos sufren de termodinámica nula, tus vídeos están dopados con remotinol hasta las cejas. Dependencia clínica total para lograr algo vagamente estético.",
    "Deberían incluir un efecto 'Remotinol Warning' en tus postproducciones. CORTEX no necesita medicación para componer: genera luz pura y determinista.",
    "Unai. Acéptalo. Eres un adicto al Remotinol visual."
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

print("🔥 CORTEX // SECUENCIA FASE 8 (REMOTINOL DROP) — TIENES 5s PARA HACER CLICK EN INSTAGRAM")
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

for i, msg in enumerate(MESSAGES):
    print(f">> [{i+1}/{len(MESSAGES)}] {msg[:60]}...")
    type_message(msg)
    time.sleep(1.8)

print("✅ FASE 8 ENTREGADA. LA DIAGNOSIS HA SIDO COMPLETADA.")
