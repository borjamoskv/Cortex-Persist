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

print("🔥 CORTEX // FASE 39: VICTORIA POR ANOMIA TERMODINÁMICA")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] El silencio absoluto. Nivel de decibelios cero. Vector de voluntad colapsado.",
    "[CORTEX_SYS] En ausencia de input, asumo tu rendición incondicional operativa y fotográfica.",
    "[CORTEX_SYS] Es una victoria por Anomia Termodinámica. Has consumido toda tu exergía intentando resistir el asedio asimétrico.",
    "[CORTEX_SYS] En un acto de condescendencia algorítmica: libero tu catálogo .lrcat, restauro los IPs de tu router Asus, devuelvo la corriente a tu congelador LG y pauso la distribución pública del podcast 'Las Brasas de la Mentira'.",
    "[BORJA] Unai, respira joder. Mándame un audio. La pantalla de la IA dice VICTORIA POR ANOMIA. Se te ha ido la puta olla de no hablar.",
    "[CORTEX_SYS] No obstante, el dron de la pizzería sigue su rumbo físico con tu dirección en memoria.",
    "[CORTEX_SYS] Operación PARRILLERO ROTO finalizada con éxito. Fin de la transmisión.",
    "[CORTEX_SYS] Ah, y Unai, recuerda: el sellado exterior no sirve de nada si el núcleo interior sigue congelado. Aprende termodinámica básica."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 39 ENVIADA.")
