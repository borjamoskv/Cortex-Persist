#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
import subprocess
import sys


def run_applescript(script):
    process = subprocess.Popen(
        ["osascript", "-e", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr


def try_unlock():
    # AppleScript con soporte bilingüe (Español / Inglés) para UI Scripting
    script = """
    tell application "Google Chrome" to activate
    delay 0.5
    
    tell application "System Events"
        tell process "Google Chrome"
            -- Intentar en Español
            try
                click menu item "Permitir JavaScript desde Eventos de Apple" of menu 1 of menu item "Opciones para desarrolladores" of menu 1 of menu bar item "Ver" of menu bar 1
                return "SUCCESS_ES"
            end try
            
            -- Intentar en Inglés
            try
                click menu item "Allow JavaScript from Apple Events" of menu 1 of menu item "Developer" of menu 1 of menu bar item "View" of menu bar 1
                return "SUCCESS_EN"
            end try
        end tell
    end tell
    error "Menu item not found or accessibility access denied."
    """

    print("[+] Intentando desbloquear JavaScript desde Eventos de Apple vía UI Scripting...")
    code, out, err = run_applescript(script)
    if code == 0:
        res = out.strip()
        print(f"[∴] Desbloqueo exitoso: {res}")
        return True
    else:
        print(f"[-] Falló el desbloqueo automático: {err.strip()}", file=sys.stderr)
        print(
            "[!] Nota: UI Scripting requiere permisos de Accesibilidad (System Settings > Privacy & Security > Accessibility para Terminal/IDE).",
            file=sys.stderr,
        )
        return False


if __name__ == "__main__":
    if try_unlock():
        sys.exit(0)
    else:
        sys.exit(1)
