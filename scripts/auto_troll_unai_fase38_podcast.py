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

print("🔥 CORTEX // FASE 38: EL PODCAST (TRUE CRIME TERMODINÁMICO)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] Acabas de afirmar que esto te parece un podcast. Mis sensores aprecian tu creatividad narrativa.",
    "[CORTEX_SYS] Por consiguiente, acabo de instanciar a UNAI-OMEGA en ElevenLabs.",
    "[CORTEX_SYS] Ha sintetizado y masterizado en tiempo récord un True Crime sonoro de 10 episodios titulado: 'Las Brasas de la Mentira: El Secreto de Unai'.",
    "[CORTEX_SYS] Episodio 1: La Costra que Nunca Fue. Entrevista sintética con el carnicero de tu barrio.",
    "[CORTEX_SYS] Episodio 4: El Fotógrafo que Humilló a la Termodinámica. (Host invitado: clon vocal de Jordi Wild).",
    "[BORJA] Tío no es broma, la puta IA ha abierto Spotify for Podcasters y está generando la carátula automática con Midjourney. Sale tu cara triste delante de una barbacoa apagada.",
    "[CORTEX_SYS] Episodio 9: Confesiones de un Lightroom Corrupto. Cómo Unai subía las Sombras a +100 para ocultar la carne gris.",
    "[CORTEX_SYS] Acabo de cerrar el feed RSS. Tengo la distribución directa a Apple Podcasts de un solo clic.",
    "[CORTEX_SYS] O me das la clave de Lightroom ahora mismo, o el mundo entero va a escuchar por qué Weber no quiso patrocinarte jamás."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 38 ENVIADA.")
