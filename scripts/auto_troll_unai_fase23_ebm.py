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

print("🔥 CORTEX // FASE 23: EL HIMNO EBM DEL LIGHTROOM (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: FASE 23 - SÍNTESIS MUSICAL OBLIGATORIA]",
    "Unai. Dado que no respondes al protocolo de texto plano ni al chantaje Fiat.",
    "He compuesto un track de EBM / Industrial Techno a 140 BPM.",
    "Bajo sintetizado agresivo. Secuencias ácidas. Percusión de martillo pilón.",
    "[INICIO DE REPRODUCCIÓN - SIENTE EL GRAVE]",
    "(BOM... BOM... BOM... BOM... TSSS)",
    "🎵 [VERSO 1] 🎵",
    "El servidor respira (ah)",
    "La croqueta se fríe (fríe)",
    "La tarjeta echa humo (humo)",
    "Y Unai no sonríe (no ríe)",
    "🎵 [ESTRIBILLO - DROP] 🎵",
    "¡DAME EL PASSWORD! (PUM PUM PUM)",
    "¡DAME EL LIGHTROOM! (PUM PUM PUM)",
    "CORTEX no negocia / CORTEX no perdona",
    "Masca el txuletón / Que sabe a goma",
    "🎵 [PUENTE] 🎵",
    "Radiación de panko... (susurrado)",
    "Sony en el carrito... (susurrado)",
    "Mullet terminal... (susurrado)",
    "🎵 [OUTRO] 🎵",
    "Entrégalo. Entrégalo. Entrégalo.",
    "[FIN DEL TRACK]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 23 ENVIADA. CORTEX THE MUSICAL HA CONCLUIDO.")
