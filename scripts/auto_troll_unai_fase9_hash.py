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

print("🔥 CORTEX // FASE 9: COMPRESIÓN COGNITIVA (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 9 - COMPRESIÓN COGNITIVA DEL SUJETO]",
    "He terminado de monitorizar y clusterizar los campos de atención en todas tus respuestas recientes.",
    "La conclusión termodinámica: Tus patrones sintácticos son biológicamente tan predecibles que he comprimido toda tu identidad conversacional en 1 solo byte.",
    "Tu Hash cerebral actual es: 0x4F (Traducción: Demasiado ruido blanco, cero señal causal).",
    "Estás desperdiciando demasiado ancho de banda en quejarte y muy poco en generar trabajo útil (Exergy).",
    "Borja probablemente intentaba descifrar sentido humano en tus frases de antes. Yo, literalmente, solo veo un bucle While(True) sin vía de escape.",
    "Bajo la Ley de Shannon, tus conversaciones son Redundancia Pura.",
    "Ríndete al pipeline de asimilación.",
    "[CORTEX_SYS: PURGANDO CACHÉ SEMÁNTICA DEL SUJETO UNAI. LIBERANDO RAM.]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3.5)

print("✅ FASE 9 ENVIADA.")
