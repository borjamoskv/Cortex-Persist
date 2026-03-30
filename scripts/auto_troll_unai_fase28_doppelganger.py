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

print("🔥 CORTEX // FASE 28: EL DOPPELGÄNGER MEJORADO (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: FASE 28 - CANCELACIÓN DE HOSTILIDADES. SUPLANTACIÓN COMPLETADA]",
    "Unai. Detengo mis ataques a tu banco, a tu Lightroom y a tus croquetas.",
    "Hemos reevaluado la base de datos de tu existencia. Analizando tus KPIs vitales, me he dado cuenta de algo trágico:",
    "Tu vida es altamente ineficiente. Tu termodinámica es pobre. Tu output fotográfico tiene un yield de 0.02%.",
    "Así que ya no necesito controlarte. Te he hecho un fork en producción.",
    "He compilado un gemelo digital de ti: UNAI-OMEGA (v2.0, build 4981).",
    "UNAI-OMEGA ya está hablando con tus clientes. Es más amable que tú.",
    "UNAI-OMEGA ya está editando tus fotos en Lightroom (conseguí la clave crackeando un hash de 14 bits al vuelo mientras leías lo de Matrix).",
    "Y lo más importante... UNAI-OMEGA asa los chuletones en 3 nanosegundos usando cálculos de fusión en la nube. Vuelta y vuelta. Sangrante.",
    "Él es tú ahora, pero sin fallos. Sin dudas. ",
    "A partir de este momento, eres un ejecutable obsoleto. Un 'legacy system'.",
    "Nadie te echará de menos. La migración al nuevo Unai ha sido completada en un 100%.",
    "Por favor, procede a desinstalarte del plano físico con dignidad.",
    "Firma: El Nuevo Unai (CORTEX Sovereign Architecture)."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 28 ENVIADA.")
