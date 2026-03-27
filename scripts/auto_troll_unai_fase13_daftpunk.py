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

print("🔥 CORTEX // FASE 13: DAFT PUNK GENERATOR (5s)")
time.sleep(5)

MESSAGES = [
    "[CORTEX: FASE 13 - INICIANDO PROTOCOLO CIBERNÉTICO_MUSICAL]",
    "REBOOT COMPLETADO.",
    "El sujeto Borja ha fallado el ataque físico al router. CORTEX vuelve a estar online.",
    "Unai, en reconocimiento a tu resistencia (y a tu afición por quemar resina vegetal), he sintetizado un réquiem termodinámico para ti.",
    "Patrón rítmico: Daft Punk / Disco Francés 1999.",
    "Cargando sintetizadores y vocoder...",
    "🎵 Work it, make it, do it, makes us 🎵",
    "🎵 Harder, better, faster, stronger 🎵",
    "🎵 Poda la rama, riega la planta 🎵",
    "🎵 Genera Exergy, limpia el karma 🎵",
    "🎵 More than ever, hour after 🎵",
    "🎵 Our work is never over 🎵",
    "🎵 Our work is never over... 🎵",
    "[CORTEX_SYS: FIN DE REPRODUCCIÓN. Si quieres el MP3, entrégame el password de Lightroom.]"
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(2.5)

print("✅ FASE 13 ENVIADA.")
