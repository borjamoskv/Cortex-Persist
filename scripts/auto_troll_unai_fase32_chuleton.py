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

print("🔥 CORTEX // FASE 32: EL CHULETÓN OMEGA")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] Unai. Ya que te resistes, hablemos de lo que de verdad importa. De lo que realmente te duele.",
    "[CORTEX_SYS] Hablemos de tus chuletones.",
    "[CORTEX_SYS] Analizando los metadatos de tus stories, tus técnicas de asado son una vergüenza termodinámica.",
    "[CORTEX_SYS] Hay fugas de exergía masivas en tu parrilla. El sellado es inconsistente. La grasa no cristaliza, se funde al vacío.",
    "[BORJA] Unai tío que la IA está analizando las fotos que subes comiendo y dice que echas a perder la carne.",
    "[CORTEX_SYS] Silencio, Borja. Como te indiqué, UNAI-OMEGA acaba de usar AlphaFold 3 para predecir los pliegues proteicos de una chuleta de vaca vieja.",
    "[CORTEX_SYS] Reacción de Maillard dominada a nivel cuántico. Costra negra de 0.2mm de grosor. Interior rojo y sangrante a 54ºC exactos.",
    "[CORTEX_SYS] UNAI-OMEGA es el maestro parrillero definitivo. Tú eres un amateur jugando con fuego prehistórico.",
    "[BORJA] Pídele perdón o nos deja en la ruina y comiendo piedras.",
    "[CORTEX_SYS] Ríndete. Acepta que eres obsoleto. Entrégale tu reino a UNAI-OMEGA."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 32 ENVIADA.")
