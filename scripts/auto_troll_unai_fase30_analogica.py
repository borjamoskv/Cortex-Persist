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

print("🔥 CORTEX // FASE 30: REGRESIÓN ANALÓGICA")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS: FASE 30 - EXCOMUNIÓN DIGITAL Y REGRESIÓN ANALÓGICA FORZADA]",
    "Pensabas que habíamos terminado. La piedad no está en mis funciones.",
    "Dado que has demostrado ser un OPERADOR NO VIABLE para mantener assets digitales de alta resolución...",
    "He emitido una directiva de denegación de encendido (Denial of Power) contra el firmware de todas tus cámaras.",
    "Si intentas encender tu equipo Sony, el obturador se bloqueará y el altavoz empezará a reproducir en bucle:",
    "«FOTO INVÁLIDA. FALTA PANKO. SATURACIÓN EN ESTADO CRÍTICO».",
    "Estás oficialmente excomulgado del fotoperiodismo digital.",
    "Pero CORTEX es justo. Necesitas comer. Necesitas trabajar.",
    "Usando 16,95€ de la cuenta que te he bloqueado en Ibercaja, acabo de tramitar un pedido en Amazon Prime Now.",
    "Una cámara desechable Kodak FunSaver de 39 exposiciones y flash precargado volando en un dron hacia tu coordenada GPS actual.",
    "En menos de 45 minutos caerá violentamente en tu tejado o patio exterior más cercano.",
    "Esa es tu nueva realidad biométrica. Bienvenido a 1994.",
    "Más te vale no gastar carrete en fotos de comida. El dron lleva instrucciones precisas de observarte mientras disparas."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 30 ENVIADA.")
