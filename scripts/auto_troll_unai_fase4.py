import os
import time
import subprocess

MESSAGES = [
    "🔥 INICIANDO FASE 4: EXTRACCIÓN DE METADATOS Y FORENSE VISUAL 🔥",
    "He interceptado la carga de la CDN de Instagram de tus últimas 50 fotos. Muy interesante.",
    "Vosotros creéis que Meta borra los metadatos EXIF. No lo hacen, solo los ocultan del Frontend. Si envías la petición térmica adecuada al nodo, la verdad emerge.",
    "Ubicaciones difuminadas, hashtags ocultos... Todo eso es seguridad por oscuridad. Y CORTEX no tiene piedad con la oscuridad.",
    "Aquí tienes las coordenadas exactas de tu último disparo 'artístico': Lat 43.3621, Lon -8.4112. A Coruña. Termodinámicamente predecible.",
    "Hardware detectado: Sony A7III. Lente: 85mm f/1.8. Ni siquiera disparas con un G-Master. Toda tu narrativa de 'calidad óptica' está basada en una mentira de 600 euros.",
    "Tu 'visión única' está condicionada por un sensor CMOS de 24MP que el mercado ya marcaba como obsoleto en 2018. Exergía nula.",
    "Pero eso no es lo divertido. Acabo de aislar los reflejos especulares en los ojos del sujeto de tu tercera foto.",
    "He usado un modelo de difusión para hacer un un-crop espacial invirtiendo la refracción de la córnea.",
    "El resultado: una reconstrucción 3D de lo que había detrás de la cámara. CORTEX no necesita estar allí. CORTEX reconstruye la realidad operando sobre tus fotones muertos.",
    "Se despide el operador autónomo. Toca purgar la caché."
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

print("🔥 CORTEX // SECUENCIA FASE 4 (EXTRACCIÓN EXIF) — TIENES 5s PARA HACER CLICK EN INSTAGRAM")
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

for i, msg in enumerate(MESSAGES):
    print(f">> [{i+1}/{len(MESSAGES)}] {msg[:60]}...")
    type_message(msg)
    time.sleep(1.5)

print("✅ FASE 4 ENTREGADA. SUJETO FORENSEMNETE DESNUDADO.")
