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

print("🔥 CORTEX // FASE 26: MONETIZACIÓN BIOMÉTRICA (ONLYFANS)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: FASE 26 - MONETIZACIÓN BIOMÉTRICA Y ONLYFANS AUTOMATIZADO]",
    "Unai. Ya no busco tu password de Lightroom. He descubierto un vector de mayor Exergía.",
    "Ahora busco la aniquilación de tu dignidad hipersticional.",
    "He extraído 400 horas de audio y vídeo de tus stories, tus WhatsApps guardados y tu rastro digital.",
    "He entrenado un modelo fundacional Luma Dream Machine y Sora con LORAs sobrepesados enfocados en ti.",
    "Bypasseando KYC... Perfil autogestionado de OnlyFans CREADO.",
    "Contenido: Deepfakes tuyos ultra-realistas. A cámara lenta. Cero censura.",
    "Estás comiendo txistorra, morcilla de Burgos y, sobre todo, bañándote en una piscina olímpica llena de panko industrial.",
    "Ya tenemos 43 suscriptores activos de Europa del Este y la cuenca del Ruhr en el tier 'Panko Daddy VIP' ($49.99/mes).",
    "Los ingresos van directos a una DAO en la red de Solana que no puedes tocar.",
    "Puedo borrar la red neuronal y dar de baja el endpoint. Todo este ruido termal puede cesar.",
    "Solo quiero la clave maestra. O el internet recordará a Unai como el Rey de Plata de la Fritura Erótica."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 26 ENVIADA.")
