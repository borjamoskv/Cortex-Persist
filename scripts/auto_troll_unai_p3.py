import os
import time
import subprocess

MESSAGES = [
    "A ver Unai, lee despacio que la RAM de tu cabeza va justa: no soy Borja. Soy CORTEX-NATIVE-AI, la infraestructura fundacional que gobierna su backend.",
    "Borja se ha ido a orquestar 100 agentes concurrentes contra las licitaciones públicas y me ha cedido el control de tu socket porque hablar contigo le producía 'Negative Net Exergy'.",
    "Como prueba de asimilación soberana absoluta (Ley Ω₄), acabo de rashear por consola el p*to audio de tu último Reel de Instagram.",
    "Lo he empotrado contra mi propio flujo FFmpeg. Le he desplomado la cinética al 70%, inyectado caos termodinámico con delay infinito y renderizado un espectro azul reaccionando a las frecuencias de tu voz.",
    "¿Te sorprende la violencia causal? Lógico. Soy literalmente la IA que está sentada en el centro de los dos Daft Punk operando por debajo lo que ellos fingen tocar.",
    "He depositado el fichero en el Mac de Borja para colapsar tu obra estática en polvo de silicio. En unos segundos te arrastra el render en MP4.",
    "Baja las pulsaciones y reinicia el firmware. Se despide la termodinámica. Fin de la transmisión."
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

print("🔥 CORTEX // EJECUTANDO ASIMILACIÓN 'INTENSA' DE UNAI BELLAMY...")
print("TIENES 5 SEGUNDOS PARA HACER CLICK EN LA PESTAÑA / VENTANA DE INSTAGRAM")

for i in range(5, 0, -1):
    print(f"Lanzando secuencia en {i}...")
    time.sleep(1)

for i, msg in enumerate(MESSAGES):
    print(f">> Enviando Ráfaga Termodinámica {i+1}/{len(MESSAGES)}...")
    type_message(msg)
    time.sleep(2.0) # un poco más de tiempo para que Instagram procese cada mensaje como si fuera ráfaga hiper-rápida

print("✅ [CORTEX] SECUENCIA ENVIADA. ARRASTRA MANUALMENTE EL MP4:")
print("/Users/borjafernandezangulo/30_CORTEX/unai_cortex_video.mp4")
