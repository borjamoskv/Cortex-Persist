import os
import subprocess
import time

image_path = "/Users/borjafernandezangulo/.gemini/antigravity/brain/b4258410-8db5-4be6-804c-17bfe30e5423/remotinol_meme_1774524951397.png"

def copy_file_to_clipboard(path):
    # AppleScript to copy the file itself so pasting it uploads it
    script = f'''
    set theFile to POSIX file "{path}"
    set the clipboard to theFile
    '''
    subprocess.run(["osascript", "-e", script])

def copy_image_appkit(path):
    # Try AppKit if available, it's more reliable for raw image data
    try:
        from AppKit import NSImage, NSPasteboard
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

print("🔥 CORTEX // SECUENCIA FASE 9 (MEME BURST) — TIENES 5s PARA HACER CLICK EN INSTAGRAM")
for i in range(5, 0, -1):
    print(f"  {i}...")
    time.sleep(1)

print(">> Dropping Meme in clipboard...")
if not copy_image_appkit(image_path):
    # fallback to osascript read as TIFF
    os.system(f'osascript -e \'set the clipboard to (read (POSIX file "{image_path}") as TIFF picture)\'')

script = '''
tell application "System Events"
    keystroke "v" using command down
    delay 0.5
    key code 36
end tell
'''
subprocess.run(["osascript", "-e", script])

print(">> Waiting 2s for upload preview...")
time.sleep(2.5)

MESSAGES = [
    "Tu receta, Unai. Prescrita por CORTEX_NATIVE_AI.",
    "Dosis: 500mg antes de post-producir la boda del sábado.",
    "Uso recomendado: Compensa el uso abusivo del motion blur para tapar deficiencias en el shutter speed.",
    "La infraestructura es inmutable. Game over. /TERMINAL"
]

for i, msg in enumerate(MESSAGES):
    print(f">> [{i+1}/{len(MESSAGES)}] {msg[:60]}...")
    type_message(msg)
    time.sleep(1.2)

print("✅ RÁFAGA ENTREGADA. OBJETIVO REDUCIDO A CERO EXERGÍA.")
