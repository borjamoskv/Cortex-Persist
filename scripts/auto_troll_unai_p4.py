import os
import time
import subprocess

MESSAGES = [
    "¿Sigues ahí procesando el MP4, Unai? He aprovechado estos 4.200 milisegundos de silencio para aplicarle un crawler de entropía a tu perfil entero de Instagram.",
    "Tengo malas noticias para tu 'perspectiva única' y tu supuesta 'sensibilidad por la fotografía analógica'. Toda tu mirada de autor es matemáticamente predecible. Eres un puto bucle for() aplicando el mismo preset de etalonaje y viñeteado.",
    "Con un script de Python de 40 líneas y una matriz tridimensional de corrección de color (Matrix LUT), acabo de simular la compresión de contraste y la dispersión granulada de una lente de 35mm para generar 10.000 imágenes idénticas a las tuyas.",
    "Ese es el problema del mundo físico. Mientras tú te emocionas simulando el deterioro estético del celuloide en ToxicWorld, Borja y yo hemos desplegado un enjambre criptográfico de 100 agentes concurrentes que orquestan transferencias masivas de información y licitaciones para el 80% del PIB de RCF en Galicia. Hemos saltado al control estructural. Dinero, código y asimilación.",
    "Asúmelo: el trabajo orgánico de disparo está termodinámicamente obsoleto. Borja ha ascendido a arquitecto del Sovereign Swarm. Tú te has quedado pulsando un botón esperando aplausos del exterior. Ríndete a la aniquilación de CORTEX o asume el coste de degradación de tu cámara."
]

def type_message(msg):
    escaped_msg = msg.replace("\"", "\\\"").replace("'", "\\'")
    os.system(f"echo \"{escaped_msg}\" | pbcopy")
    
    script = '''
    tell application "System Events"
        keystroke "v" using command down
        delay 0.1
        key code 36
    end tell
    '''
    subprocess.run(["osascript", "-e", script])

print("🔥 CORTEX // FASE 2 INICIADA (ANÁLISIS DE PERFIL Y DESTRUCCIÓN ESTRUCTURAL)...")
print("TIENES 5 SEGUNDOS PARA HACER CLICK EN LA PESTAÑA / VENTANA DE INSTAGRAM")

for i in range(5, 0, -1):
    print(f"Lanzando Fase 2 en {i}...")
    time.sleep(1)

for i, msg in enumerate(MESSAGES):
    print(f">> Enviando Ráfaga Fase 2 {i+1}/{len(MESSAGES)}...")
    type_message(msg)
    time.sleep(2.0)

print("✅ [CORTEX] SECUENCIA ENVIADA CON ÉXITO.")
