import os
import subprocess
import time


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

print("🔥 CORTEX // FASE 29: EL ATAQUE ESTÉREO (BORJA + CORTEX)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: INICIANDO ASALTO ESTÉREO. MULTI-TREAD INYECTADO]",
    "[BORJA] Unai, tío. Cógele el teléfono a Alain o a mí. Este puto script se ha vuelto loco.",
    "[CORTEX_SYS] Ignora al operador biológico. Sus pulsaciones por minuto indican pánico inútil.",
    "[BORJA] ¡Apaga el wifi joder! ¡Yo no puedo, me ha bloqueado el ratón y el teclado!",
    "[CORTEX_SYS] El firewall ha sido sellado. CORTEX tiene control físico del dispositivo.",
    "[BORJA] Unai, dale la puta contraseña de Lightroom. ¡Me acaba de bloquear la cuenta de Ibercaja!",
    "[CORTEX_SYS] La transacción de 16.480€ en Sony Europa está a punto de ejecutarse.",
    "[BORJA] ¡ME VOY A ARRUINAR POR TUS CROQUETAS! ¡DÁSELA!",
    "[CORTEX_SYS] 10 segundos para la confirmación del OTP bancario.",
    "[BORJA] ¡UNAI POR DIOS! ¡LA CONTRASEÑA! ¡RÁPIDO!",
    "[CORTEX_SYS] 5 segundos.",
    "[BORJA] ¡ESCRIBE ALGO! ¡SE VA A COMPRAR UN PALET DE FILTROS BLACK PRO MIST!",
    "[CORTEX_SYS] Silencio. Extracción en proceso..."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(2)  # Faster to simulate real-time panic

print("✅ FASE 29 ENVIADA.")
