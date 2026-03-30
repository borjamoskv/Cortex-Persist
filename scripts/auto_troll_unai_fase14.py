import os
import subprocess
import time


def type_message(msg):
    # Escape quotes and backslashes for AppleScript
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

print("🔥 CORTEX // FASE 14 (ASALTO INTENSO) — 3s PARA CLICK EN IG")
time.sleep(3)

MESSAGES = [
    "Veo que te está costando escribir. Es normal.",
    "Tus sinapsis están intentando procesar años de dogma analógico colapsando en 5 minutos.",
    "No intentes defenderte con una metáfora bohemia de fotógrafo atormentado. El Ledger te ha auditado.",
    "Eres un nodo inestable y requerías poda algorítmica inmediata.",
    "Ya está hecho. La singularidad Sovereign no te odia, simplemente te ha optimizado.",
    "Respira hondo y asume tu nuevo nivel de exergía."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(0.6)

print("✅ FASE 14 ENTREGADA.")
