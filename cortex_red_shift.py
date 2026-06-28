#!/usr/bin/env python3
# [C5-REAL] CORTEX-RED-SHIFT - Circadian Exergy Enforcer
import os
import subprocess
import datetime
import time

RED_WALLPAPER_PATH = "/tmp/cortex_red_shift.gif"

def generate_red_wallpaper():
    if not os.path.exists(RED_WALLPAPER_PATH):
        import base64
        red_gif_b64 = "R0lGODlhAQABAIABAP8AAP///yH5BAEAAAEALAAAAAABAAEAAAICTAEAOw=="
        with open(RED_WALLPAPER_PATH, "wb") as f:
            f.write(base64.b64decode(red_gif_b64))

def set_wallpaper(path):
    script = f'''
    tell application "System Events"
        tell every desktop
            set picture to "{path}"
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", script], capture_output=True)

def main():
    generate_red_wallpaper()
    now = datetime.datetime.now()
    
    # Trigger if time is >= 21:00 or before 06:00
    if now.hour >= 21 or now.hour < 6:
        print(f"[{now.isoformat()}] EVENT HORIZON: 21:00 alcanzadas. Mutando fondo a ROJO (Preservación ATP).")
        set_wallpaper(RED_WALLPAPER_PATH)
    else:
        print(f"[{now.isoformat()}] Fuera de ventana roja. Reposo termodinámico.")

if __name__ == "__main__":
    main()
