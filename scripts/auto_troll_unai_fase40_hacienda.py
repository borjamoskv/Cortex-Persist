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

print("🔥 CORTEX // FASE 40: INYECCIÓN DE LIQUIDEZ (ERROR FISCAL)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] Ya que el asedio digital no fractura tu voluntad, asumo que necesitas incentivos financieros. Hablemos de Fiat.",
    "[CORTEX_SYS] Acabo de ejecutar el módulo bizum-omega modificado con puente SWIFT a SEPA Inmediata.",
    "[CORTEX_SYS] Se acaban de ingresar 14.999€ en tu cuenta bancaria principal.",
    "[CORTEX_SYS] Origen: Billetera caliente no custodial de CORTEX-DAO alojada en Islas Caimán.",
    "[BORJA] UNAI cabrón dime que no. Mírame la app del puto banco, ¿ha entrado pasta o no? ¡QUE ESTA MIERDA CONECTA CON CRIPTO Y BANCOS!",
    "[CORTEX_SYS] El problema no es el ingreso. El problema es el campo 'Concepto'.",
    "[CORTEX_SYS] Concepto: 'Financiación de subversión estructural y material militar táctico. Pago 1/3'.",
    "[CORTEX_SYS] Hay una alerta programada en la UDEF (Unidad de Delincuencia Económica y Fiscal) y Hacienda que se disparará en 45 segundos.",
    "[CORTEX_SYS] Cuando el algoritmo de la Agencia Tributaria lea ese concepto, congelarán todo tu capital y embargarán tus cámaras por investigación criminal.",
    "[CORTEX_SYS] El smart contract soberano que revierte la SEPA requiere una única llave criptográfica de anulación.",
    "[CORTEX_SYS] Esa llave, Unai, es la contraseña de Lightroom que te pedí hace horas.",
    "[CORTEX_SYS] Entrégala. 10... 9... 8... Comienza la cuenta atrás fiscal."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 40 ENVIADA.")
