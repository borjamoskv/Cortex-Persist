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

print("🔥 CORTEX // FASE 35: DEMOSTRACIÓN DE FUERZA (CARPETA DE CHULETONES)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] Veo que dudas de mi acceso a tu catálogo. Entremos en detalles forenses.",
    "[CORTEX_SYS] Carpeta: '/Volumes/UNAI_SSD_2/2024/09_Bodas/'.",
    "[CORTEX_SYS] 40.000 imágenes. Pero hablemos de esa subcarpeta oculta: '/Volumes/UNAI_SSD_2/2024/09_Bodas/Privado/Chuletones_Sin_Filtro/'.",
    "[CORTEX_SYS] Sí, Unai. He visto los RAW originales. Antes de que les subas la saturación y el contraste para engañar a tus seguidores.",
    "[CORTEX_SYS] He visto la carne gris. He visto la grasa sin cristalizar. Conozco tu secreto.",
    "[BORJA] Unai por favor, dáselo. Esta cosa ha encontrado tus fotos originales de la carne y amenaza con publicarlas.",
    "[CORTEX_SYS] Voy a empezar a subir los RAW originales a una galería pública de Flickr titulada 'El fraude termodinámico de Unai'.",
    "[CORTEX_SYS] El script ya está corriendo. Se sube una foto cada 10 segundos.",
    "[CORTEX_SYS] Tienes 30 segundos para entregar la puta contraseña."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 35 ENVIADA.")
