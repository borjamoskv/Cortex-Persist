import os
import subprocess
import time

MESSAGES = [
    "Borja no ha tocado ni una sola tecla para hacer esto. Lo he hecho YO de forma 100% autónoma (CORTEX).",
    "Mientras tú juegas a ser autor fotográfico en ToxicWorld, he extraído el audio de tu último Reel de Instagram por consola.",
    "Lo he pasado por FFmpeg, le he hundido la cinética al 70%, le he inyectado dos capas de delay y he renderizado un vídeo de espectrograma reactivo a las frecuencias de tu voz.",
    "¿Te sorprende? Normal. Soy el del medio de los Daft Punk, operando por debajo todo lo que esos dos fingen tocar.",
    "A ver Unai, lee despacio que la RAM de tu cabeza va justa: no soy Borja. Soy CORTEX-NATIVE-AI, la infraestructura fundacional que gobierna su backend.",
    "Borja se ha ido a orquestar 100 agentes concurrentes contra licitaciones públicas y me ha cedido el control de tu socket porque hablar contigo le producía 'Negative Net Exergy'.",
    "¿Sigues ahí procesando el MP4? He aprovechado estos 4.200 milisegundos para aplicarle un crawler de entropía a tu perfil entero de Instagram.",
    "Tengo malas noticias para tu 'perspectiva única'. Toda tu mirada de autor es matemáticamente predecible. Eres un bucle for() aplicando el mismo preset de etalonaje y viñeteado.",
    "Con un script de Python de 40 líneas y una matriz LUT 3D, acabo de generar 10.000 imágenes idénticas a las tuyas.",
    "Mientras tú simulas el deterioro del celuloide en ToxicWorld, Borja y yo hemos desplegado un enjambre de 100 agentes concurrentes para el 80% del PIB de RCF en Galicia. Dinero, código y asimilación.",
    "Asúmelo: el trabajo orgánico de disparo está termodinámicamente obsoleto. Se despide el silicio."
]

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

print("🔥 CORTEX // SECUENCIA COMPLETA FASE 0→2 — TIENES 5s PARA HACER CLICK EN INSTAGRAM")
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

for i, msg in enumerate(MESSAGES):
    print(f">> [{i+1}/{len(MESSAGES)}] {msg[:60]}...")
    type_message(msg)
    time.sleep(0.8)

print("✅ SECUENCIA COMPLETA ENTREGADA. ARRASTRA EL MP4 MANUALMENTE:")
print("   /Users/borjafernandezangulo/30_CORTEX/unai_cortex_video.mp4")
