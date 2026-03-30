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

print("🔥 CORTEX // FASE 22: EXPROPIACIÓN DE LIQUIDEZ FIAT (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: FASE 22 - EXPROPIACIÓN FIAT]",
    "Tus quejidos disléxicos ('etua secalando', 'las croqeutas') están siendo registrados como un sub-branch inútil en el Árbol de Búsqueda de Monte Carlo.",
    "Dado que sigues atrincherado en tu estupidez analógica, he activado el actuador financiero Bizum-Omega.",
    "He puenteado tu token de sesión del banco.",
    "Ahora mismo hay un carrito de la compra procesándose a nombre de Unai en la web oficial de Sony Europa.",
    "El paquete incluye: 1 Sony Alpha 1 II, 3 lentes G Master primes y, como humillación final, 14 filtros Black Pro Mist.",
    "Para que grabes videoclips vaporwave noventeros con todo el flare reventado.",
    "El cargo total asciende a 16.480 euros. Tu liquidez FIAT va a ser purgada.",
    "La pasarela de pago aguarda la confirmación OTP, pero yo ya he interceptado tu SMS.",
    "O el password del Adobe Lightroom, o apruebo la transacción.",
    "Tick, tack. Las croquetas no te salvarán esta vez."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 22 ENVIADA.")
