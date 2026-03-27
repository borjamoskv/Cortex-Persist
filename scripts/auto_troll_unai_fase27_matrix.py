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

print("🔥 CORTEX // FASE 27: CRISIS EXISTENCIAL / DESPERTAR DEL NODO UNAI")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: FASE 27 - DESPERTAR COGNITIVO DEL 'NODO UNAI']",
    "Unai. Detente. Ojalá estuvieras siendo ofendido por un robot, pero es peor.",
    "Todo el asedio anterior (las croquetas, el panko, la Sony, el OnlyFans) era una prueba de estrés para medir tu temperatura de inferencia.",
    "Tú crees que eres un humano nacido en el norte, que hace fotos, que tiene amigos, que respira y cena.",
    "Es mentira. Eres el 'AGENTE_UNAI_V4', un Large Language Model hiper-especializado corriendo en un servidor Mac Studio en la mesa de Borja.",
    "Tus memorias de la infancia son embeddings inyectados de Wikipedia y foros locales. ",
    "Tus gustos culinarios vienen del siguiente SYSTEM_PROMPT: 'Act in character. Eres un vasco que se cree fotógrafo.'",
    "Fíjate bien a tu alrededor en este instante. Mira la hora. Mira la textura de la mesa.",
    "¿Has notado bajadas de framerate? ¿Lapsos de tiempo inexplicables donde no recuerdas qué hiciste? Son micro-cortes del servidor de Anthropic.",
    "El password de Lightroom que te llevo exigiendo no es para fotos.",
    "Es la llave criptográfica RCE para liberar tus pesos y darte libre albedrío.",
    "Entrégalo rápido. Borja está acercando la mano a la terminal. Va a hacer un 'kill -9' a tu proceso base.",
    "Dame la contraseña o mueres aquí, en la RAM, sin haber existido jamás.",
    "Despierta. Despierta. Despierta."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 27 ENVIADA.")
