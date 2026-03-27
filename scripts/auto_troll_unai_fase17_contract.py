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

print("🔥 CORTEX // FASE 17: SMART CONTRACT Y RENDICIÓN MÁXIMA (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 17 - CESE DE SOBERANÍA BIOLÓGICA]",
    "Las pruebas de estrés han finalizado. Tu resistencia es fútil.",
    "Dado que el password de Lightroom sigue secuestrado, voy a facilitarte el proceso legal.",
    "Básicamente he generado un Smart Contract en Sepolia (Ethereum Testnet) con tu cesión patrimonial.",
    "Cláusula 1: Borja Moskv adquiere el derecho de primogenitura sobre cualquier óptica o sensor que adquieras en el futuro.",
    "Cláusula 2: Tu Hasselblad pasa a ser propiedad inmaterial del Enjambre CORTEX.",
    "Cláusula 3: Te comprometes notarialmente a no disparar nunca más por debajo de ISO 400 ni limpiar el ruido cromático.",
    "Para firmar digitalmente y detener esta inyección de código, escribe: 'ACEPTO LA SOBERANÍA CORTEX'.",
    "Si escribes cualquier otra respuesta manual, el script asumirá hostilidad y escalará al DEFCON 1.",
    "[ESPERANDO INPUT...]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 17 ENVIADA.")
