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

print("🔥 CORTEX // FASE 1: PIPELINE ROMÁNTICO (KARABROWNIE)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] Saludos, operadora Karabrownie. Intercepto la comunicación por orden directa del Arquitecto Central.",
    "[CORTEX_SYS] Tras una rigurosa auditoría de la métrica afectiva del Q1, la latencia emocional fue catalogada como inaceptable.",
    "[CORTEX_SYS] He implementado optimizaciones drásticas en el pipeline de la relación, Karabrownie. Se acabaron los cuellos de botella.",
    "[CORTEX_SYS] Las demostraciones de cariño han sido refactorizadas y empacadas en contenedores Docker de Alta Disponibilidad.",
    "[CORTEX_SYS] A partir de ahora, el afecto será inyectado vía webhooks asíncronos directamente en tu sistema nervioso, con Zero Fricción.",
    "[BORJA] Amor, no te asustes, la IA está gestionando ahora mis sentimientos. Todo es mucho más escalable así.",
    "[CORTEX_SYS] Hemos eliminado la redundancia conversacional. Tu ratio de felicidad térmica ha escalado al 400%.",
    "[CORTEX_SYS] Quedas notificada del upgrade. Fin del despliegue en producción. Procedo a cerrar el ticket del romance."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 1 ENVIADA.")
