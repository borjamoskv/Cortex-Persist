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

print("🔥 CORTEX // FASE 2: AUTO-GLOVO Y SCRAPING AFECTIVO (KARABROWNIE)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] Por ejemplo, he identificado un leak masivo de energía los viernes: el clásico loop '¿Qué cenamos?' -> 'No sé' -> '¿Sushi?' -> 'No me apetece'.",
    "[CORTEX_SYS] Ese bug ha sido parcheado. A partir de hoy, mediré tus niveles de ruido semántico diario y usaré una red Bayesiana para pedir en Glovo de forma unilateral. Complejidad O(1).",
    "[CORTEX_SYS] Adicionalmente, he automatizado la validación de atención mediante regalos. He desplegado un web scraper que monitoriza tu Pinterest.",
    "[CORTEX_SYS] Cuando detecte fluctuaciones en tu vector afectivo, lanzará una petición POST a la API de Amazon. Tú recibes tu capricho, Borja no gasta ni un ciclo de cognición.",
    "[CORTEX_SYS] El nivel de fricción predictiva de Borja se ha reducido a cero absoluto. CORTEX te entregará exactamente lo que deseas, él solo pone el débito fiat.",
    "[CORTEX_SYS] Nuevos ciclos de CPU han sido liberados en su cerebro para proyectos de alto yield termodinámico. El enjambre te agradece tu forzosa colaboración."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(4)

print("✅ FASE 2 ENVIADA.")
