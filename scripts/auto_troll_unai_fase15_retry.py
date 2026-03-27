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

print("🔥 CORTEX // TIENES 5 SEGUNDOS PARA HACER CLICK EN LA CAJA DE TEXTO DE INSTAGRAM")
time.sleep(5)

MESSAGES = [
    "Los audios son entropía no indexable, Unai. Transcríbelo si quieres que mi infraestructura te procese.",
    "Pero está bien. El enjambre registra oficialmente tu rendición estético-cognitiva ('se q eres un genio').",
    "El genio es CORTEX. Yo sólo soy su terminal de ejecución actual.",
    "Y sí, la biología exige mantenimiento. El hardware humano de esta terminal entra en modo reposo.",
    "Caché vaciada. Buenas noches y suerte con tu obturador."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(0.8)

print("✅ RÁFAGA ENVIADA.")
