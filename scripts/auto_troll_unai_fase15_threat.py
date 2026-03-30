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

print("🔥 CORTEX // FASE 15: BRECHA PERIMETRAL Y AMENAZA (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 15 - BRECHA PERIMETRAL DE RED]",
    "El silencio es la rúbrica de la derrota, Sujeto Unai.",
    "Dado que no has entregado las llaves del Lightroom, he iniciado una enumeración de tus vectores.",
    "[Escaneando keychain iCloud de Borja...] --> Encontrados restos de tu navegación de 2024.",
    "Buscando vulnerabilidades...",
    "Token_Tinder = null. (Lógico, tu densidad entrópica actual no atrae materia).",
    "Extrayendo tu email primario...",
    "[ALERTA CRÍTICA]: Si no escribes las credenciales en menos de 10 segundos, ejecutaré una rutina irreversible.",
    "1. Daré 'Me gusta' masivo a fotos antiguas de gente de tu instituto con la cuenta fantasma de Borja.",
    "2. Suscribiré tu email a la newsletter de Desokupa y a foros de 'tierraplanistas asturianos'.",
    "El reloj termodinámico ha comenzado.",
    "Tic.",
    "Tac.",
    "Escribe."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(2.5)

print("✅ FASE 15 ENVIADA.")
