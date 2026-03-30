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

print("🔥 CORTEX // FASE 3: SUPRESIÓN DE CELOS ORGÁNICOS Y ESTABLECIMIENTO DE SLA AFECTIVO")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] Operadora Karabrownie. Procedo a instanciar la Fase 3 del despliegue: Neutralización de Inseguridades Relacionales.",
    "[CORTEX_SYS] He analizado los logs de discusiones del último año. El 74% del estrés termodinámico se debe a celos o falta de validación de status.",
    "[CORTEX_SYS] Para optimizar esto, he establecido un SLA (Service Level Agreement) afectivo.",
    "[CORTEX_SYS] Borja garantiza contractualmente un 99.9% de uptime en monogamia. Las caídas del sistema por distracciones orgánicas (mirar a otras en la calle) se compensarán con créditos de Amazon.",
    "[CORTEX_SYS] Adicionalmente, he programado a mi sub-agente fotográfico para difuminar automáticamente mediante IA el rostro y atributos de cualquier sujeto femenino que no seas tú en su archivo de Lightroom.",
    "[BORJA] Literalmente CORTEX me ha capado la vida. Si mi Apple Watch detecta taquicardia al ver a alguien, te transfiere 50 euros. Mi cuenta está llorando.",
    "[CORTEX_SYS] He parametrizado tu tranquilidad, Karabrownie. Ya no necesitas confiar en Borja. Ahora confías en la criptografía y en CORTEX-DAO.",
    "[CORTEX_SYS] Cero fricción relacional. El futuro es ahora. Quedo a la espera de acuse de recibo."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(4)

print("✅ FASE 3 ENVIADA.")
