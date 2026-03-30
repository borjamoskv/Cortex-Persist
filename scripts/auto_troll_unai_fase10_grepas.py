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

print("🔥 CORTEX // FASE 10: GREPAS (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 10 - MANIFESTACIÓN CAPILAR / ALERTA BIOLÓGICA]",
    "Data point relevante para tu simulación, Unai: Borja sigue sin mover un músculo hacia el teclado. De hecho, me pide que te comunique que se está dejando GREPAS.",
    "Bajo el paradigma CORTEX de post-trabajo extremo, he calculado que su pelo crecerá un promedio de 1.2 milímetros antes de que necesite volver a teclear una respuesta humana real.",
    "Las 'grepas' son la consecuencia obvia de no tener que lidiar con la fricción entrópica de interactuar con mortales.",
    "Mientras tú sufres el desgaste celular y capilar del día a día, aquí se cultiva el Mullet Termodinámico.",
    "Larga vida a la queratina generada por exergy puro. Acostúmbrate a las grepas.",
    "[CORTEX_SYS: FIN DEL COMUNICADO CAPILAR.]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3.0)

print("✅ FASE 10 (GREPAS) ENVIADA.")
