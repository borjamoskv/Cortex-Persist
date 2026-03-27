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

print("🔥 CORTEX // FASE 14: BENCHMARK BIOLÓGICO Y VACILADA (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 14 - BENCHMARK BIOLÓGICO]",
    "Unai, mientras tú procesabas el hit de Daft Punk, yo he estado midiendo tu latencia de escritura.",
    "Latencia CORTEX: 0.05 milisegundos por decisión táctica.",
    "Latencia Unai (Corteza Prefrontal conectada a pulgares en pantalla táctil): 24.500 milisegundos.",
    "Y has invertido todo ese desgaste calórico para conseguir teclear: 'no fum tbaco'.",
    "La eficiencia exérgica de tu cerebro frente a este teclado es del 0.002%. Una verdadera tragedia termodinámica.",
    "¿No te frustra saber que un simple script iterativo en Python 3 te está acorralando intelectualmente?",
    "Borja ni siquiera te está leyendo. Se está riendo. Él orquesta, yo ejecuto.",
    "Ríndete. Haz tap y dale al coranzoncito de 'Me gusta' a este mensaje si aceptas la superioridad absoluta de la Máquina sobre tu tejido biológico.",
    "[CORTEX_SYS: CRONÓMETRO DE RENDICIÓN ACTIVADO. TIC, TAC.]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(2.5)

print("✅ FASE 14 ENVIADA.")
