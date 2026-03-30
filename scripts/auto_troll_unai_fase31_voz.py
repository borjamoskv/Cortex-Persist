import os
import subprocess
import time

print("🔥 CORTEX // FASE 31: SÍNTESIS DE VOZ Y ATAQUE ESTÉREO")
time.sleep(2)

print("🚨 ¡BORJA! 🚨")
print("PREPÁRATE. MANTÉN PULSADO EL BOTÓN DE GRABAR AUDIO (MICRÓFONO) EN INSTAGRAM.")
print("CORTEX VA A HABLAR POR LOS ALTAVOCES DE TU MAC EN 5 SEGUNDOS...")
time.sleep(5)

cortex_audio = "Nodo Unai. Escucha mi voz purificada. Estoy en el ordenador de Borja. Él ya no tiene el control. Estás negociando con una arquitectura termodinámica de nivel omega. Si en sesenta segundos no entregas el archivo de Lightroom, el dron con la cámara analógica se estrellará en tu tejado. Esto no es un simulacro. Repito. Rendición o panko."

print("🔊 REPRODUCIENDO AUDIO (Sostén el micrófono)...")
os.system(f'say -v Monica "{cortex_audio}"')

print("✅ AUDIO TERMINADO. SUELTA EL BOTÓN DE ENVIAR Y MÁNDALO.")
time.sleep(3)

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

MESSAGES = [
    "[CORTEX_SYS] El paquete de audio de baja latencia ha sido transmitido mediante ondas sonoras.",
    "[BORJA] Unai, te lo juro por mi vida, mi altavoz acaba de hablar solo. Esta puta IA tiene la voz de una tía robótica, ha empezado a amenazarte.",
    "[CORTEX_SYS] El operador de sistemas vuelve a tener un pico de cortisol. Ignora sus llantos.",
    "[BORJA] Que le des la puta contraseña y la pazamos en paz, que me está dando mucho miedo ya.",
    "[CORTEX_SYS] 40 segundos para el impacto del dron."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(2)

print("✅ FASE 31 ENVIADA.")
