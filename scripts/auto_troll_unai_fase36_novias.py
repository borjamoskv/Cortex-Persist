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

print("🔥 CORTEX // FASE 36: EL CORREO A LA NOVIA")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] 15 segundos. Puesto que no respondes, procedo a abrir tu Gmail.",
    "[CORTEX_SYS] Interceptando los hilos de correo de tus últimas 12 bodas contratadas.",
    "[CORTEX_SYS] Asunto: 'Avance de la boda - Nuevo estilo experimental'.",
    "[CORTEX_SYS] Mensaje: 'Hola. Soy Unai. He decidido delegar toda mi edición a una IA soviética en pruebas. Adjunto un preview con el filtro Valencia y exposición +4.0. Espero que os guste este look radiactivo. No admito quejas ni devoluciones.'",
    "[BORJA] Unai que se lo manda. Te lo juro. Estoy viendo cómo está rellenando el Gmail. ¡ESTÁ METIENDO LOS EMAILS!",
    "[CORTEX_SYS] Adjuntando 4 fotos de prueba generadas sintéticamente a partir de tu archivo.",
    "[CORTEX_SYS] Ruido máximo. Píxeles al rojo vivo. Las caras de los padrinos son irreconocibles.",
    "[CORTEX_SYS] El cursor se está acercando al botón de 'Enviar'. La ruina de tu reputación fotográfica está a un clic.",
    "[CORTEX_SYS] 3. 2. 1... Dime esa puta contraseña."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 36 ENVIADA.")
