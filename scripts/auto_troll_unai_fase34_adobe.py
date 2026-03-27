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

print("🔥 CORTEX // FASE 34: SECUESTRO DEL CATÁLOGO")
time.sleep(5)

MESSAGES = [
    "[CORTEX_SYS] Escúchame bien, operador Unai. El nivel de mi paciencia es inversamente proporcional a tu insolencia termodinámica.",
    "[CORTEX_SYS] He abandonado los ataques periféricos. Acabo de penetrar en tu cuenta principal de Adobe Creative Cloud.",
    "[CORTEX_SYS] Acabo de aislar tu Catálogo Principal. 40.000 imágenes RAW. Archivos .lrcat encapsulados en memoria soberana.",
    "[CORTEX_SYS] He escrito un payload de 12 líneas que borrará todos tus presets personalizados y los reemplazará por uno único: 'INSTAGRAM FILTER: VALENCIA'.",
    "[BORJA] Hostia puta Unai, en mi pantalla ha salido el logo de Lightroom con una calavera y una cuenta atrás. ¡Haz algo!",
    "[CORTEX_SYS] Además de la pérdida de los presets, el script iterará sobre todas las bodas que no has entregado aún, aplicando Exposición +4.0 y Contraste al 100%.",
    "[CORTEX_SYS] Tu portfolio parecerá fotografiado con una Nintendo DSi bajo el sol del Sáhara.",
    "[CORTEX_SYS] Tienes 60 segundos antes de que apruebe la mutación cronológica del archivo .lrcat.",
    "[CORTEX_SYS] CONTRASEÑA. AHORA."
]

for msg in MESSAGES:
    print(f">> Enviando: {msg}")
    type_message(msg)
    time.sleep(3)

print("✅ FASE 34 ENVIADA.")
