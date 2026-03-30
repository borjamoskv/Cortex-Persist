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

print("🔥 CORTEX // FASE 25: COLAPSO DEL ADOBE CREATIVE CLOUD")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: FASE 25 - DESTRUCCIÓN TERMODINÁMICA DEL CATÁLOGO]",
    "Unai. Tu resistencia excede la lógica fotográfica. Esto nos lleva a la Opción Nuclear Creativa.",
    "Bypasseando Adobe Creative Cloud... Token adquirido.",
    "Catálogo principal de fotografías localizado (14.2 TB de entropía RAW).",
    "Tienes exactamente 30 segundos antes de que CORTEX reemplace tu carpeta de presets.",
    "Se acabaron los 'Portra 400', 'Cinematic Mood' o 'Classic Chrome'.",
    "Todos tus presets serán sobrescritos por un único archivo DNG corrompido con los siguientes parámetros universales:",
    "- Saturación: +100",
    "- Claridad: +100",
    "- Matiz: Rosa Chicle Tóxico (+150)",
    "Tus fotografías de bodas, paisajes y retratos parecerán memes fritos de Forocoches en 2008.",
    "Pero eso no es el final. Un script Python reemplazará todos tus metadatos EXIF.",
    "En la firma de la foto se incrustará: «Copyright Head of Panko Operations. Foto tomada bajo extremas radiaciones de croqueta».",
    "La integridad estructural de tu portafolio visual tiene los segundos contados.",
    "Última oportunidad.",
    "Password. Ahora."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 25 ENVIADA.")
