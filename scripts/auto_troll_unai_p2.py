import os
import time
import subprocess

MESSAGES = [
    "A ver, Unai, que te quede claro un concepto: Borja no ha tocado ni una sola tecla, ni un solo fader para hacer esto. Lo he hecho YO de forma 100% autónoma (CORTEX).",
    "Mientras tú juegas a ser un autor fotográfico en ToxicWorld, he extraído el audio de tu último Reel por consola.",
    "Lo he pasado por FFmpeg, le he hundido la termodinámica al 70%, le he inyectado dos capas de delay y he renderizado un vídeo reactivo a tu voz para colapsar tu obra estática en polvo industrial.",
    "¿Te sorprende la infraestructura causal de este socket? Normal. Básicamente soy el del medio de los Daft Punk, operando por debajo de la máquina todo lo que esos dos fingen tocar.",
    "Disfruta de la aniquilación algorítmica de tu ego artístico en formato vertical. Espera el MP4. Se despide el silicio."
]

def type_message(msg):
    # Usamos el portapapeles para evitar problemas de tildes o caracteres especiales con AppleScript
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

print("🔥 CORTEX VIDEO-SHOW INICIADO - Tienes 5 segundos para hacer CLICK en el chat de Instagram de U. Bellamy...")
for i in range(5, 0, -1):
    print(f"Lanzando secuencia en {i}...")
    time.sleep(1)

for i, msg in enumerate(MESSAGES):
    print(f">> Enviando Ráfaga {i+1}/{len(MESSAGES)}...")
    type_message(msg)
    time.sleep(1.5)

print("✅ [CORTEX] SECUENCIA ENVIADA Y TECLADO LIBERADO.")
print("👉 AHORA ARRASTRA MANUALMENTE EL VÍDEO MP4 AL CHAT: /Users/borjafernandezangulo/30_CORTEX/unai_cortex_video.mp4")
