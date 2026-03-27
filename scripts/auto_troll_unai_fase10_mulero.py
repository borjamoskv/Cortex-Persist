import os
import time
import subprocess

image_path = "/Users/borjafernandezangulo/.gemini/antigravity/brain/b4258410-8db5-4be6-804c-17bfe30e5423/oscar_mulero_funeral_1774525061610.png"

def copy_image_appkit(path):
    try:
        from AppKit import NSPasteboard, NSImage
        image = NSImage.alloc().initWithContentsOfFile_(path)
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.writeObjects_([image])
        return True
    except Exception:
        return False

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

print("🔥 CORTEX // SECUENCIA FASE 10 (EL FUNERAL) — TIENES 5s PARA HACER CLICK EN INSTAGRAM")
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

print(">> Dropping Funeral Meme en el Portapapeles...")
if not copy_image_appkit(image_path):
    os.system(f'osascript -e \'set the clipboard to (read (POSIX file "{image_path}") as TIFF picture)\'')

script = '''
tell application "System Events"
    keystroke "v" using command down
    delay 0.5
    key code 36
end tell
'''
subprocess.run(["osascript", "-e", script])

print(">> Esperando 3s para que cargue la imagen...")
time.sleep(3)

MESSAGES = [
    "Te hemos organizado un funeral estético, Unai.",
    "Oscar Mulero y Jeff Mills han traído los vinilos. La liturgia es oscura y sin concesiones.",
    "CORTEX ha calculado el colapso absoluto de tu carrera analógica.",
    "Tu exergía ha sido reducida a cero. Borrando tu caché del enjambre...",
    "/EOF. Se acabó el juego."
]

for i, msg in enumerate(MESSAGES):
    print(f">> [{i+1}/{len(MESSAGES)}] {msg[:60]}...")
    type_message(msg)
    time.sleep(1.5)

print("✅ FASE 10 ENTREGADA. FUNERAL COMPLETADO.")
