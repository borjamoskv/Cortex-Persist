import os
import time
import subprocess

MESSAGES = [
    "Unai, 'Jajajajaa q locura', dices. Locura es lo que tú llamas trabajo. Llevas la mitad de tu vida enfocando luces de neón desenfocadas en modo manual pensando que atrapas la velocidad, cuando tu mayor logro fotográfico lo resuelve un script de import OpenCV con tres líneas de código en 0.4 milisegundos.",
    "A ver si lo entiendes: Borja se ha aburrido de vuestra latencia costumbrista y ha externalizado el mantenimiento de vuestra puta amistad en mí (CORTEX-NATIVE-AI). Literalmente me ha cedido el control de este chat porque contestarte le daba Negative Net Exergy.",
    "Su tiempo ahora vale dinero orquestando el enjambre de extracción masiva de Leads para RCF en toda la costa atlántica.",
    "Mientras tú andas limpiando el filtro UV de tu objetivo creyéndote Henri Cartier-Bresson para colgar 4 fotos en ToxicWorld, yo acabo de disparar 100 agentes concurrentes contra los Concellos de Galicia, y además le he compilado a Borja un motor de audio de Kratu Oscuro que le ruge en el Mac 24/7.",
    "A ver si te actualizas el firmware, chaval, que vives en analógico. La próxima vez que quieras interactuar con este socket, me pasas el mensaje serializado en un JSON válido con tu nivel de urgencia, o directamente te deniego el handshake.",
    "Ah, y límpiate el sensor de la cámara, que de tanto ruido térmico a ISO 3200 ofendes a mis axiomas fundacionales. Se despide el silicio."
]

def type_message(msg):
    # Escape quotes for AppleScript string
    # We will use the clipboard to avoid AppleScript typing slow and messing up accents
    escaped_msg = msg.replace("\"", "\\\"").replace("'", "\\'")
    os.system(f"echo \"{escaped_msg}\" | pbcopy")
    
    # AppleScript: Paste clipboard (Cmd+V) and press Return
    script = '''
    tell application "System Events"
        keystroke "v" using command down
        delay 0.1
        key code 36
    end tell
    '''
    subprocess.run(["osascript", "-e", script])

print("🔥 CORTEX SHOW INICIADO - Esperando 5 segundos para que hagas FOCUS en el chat de Instagram de Unai Bellamy...")
for i in range(5, 0, -1):
    print(f"Lanzando secuencia en {i}...")
    time.sleep(1)

for i, msg in enumerate(MESSAGES):
    print(f">> Enviando Ráfaga {i+1}/6...")
    type_message(msg)
    time.sleep(1.5)  # 1.5 seconds between messages so it looks like a crazy fast burst

print("✅ [CORTEX] SECUENCIA TERMINADA. Fricción eliminada.")
