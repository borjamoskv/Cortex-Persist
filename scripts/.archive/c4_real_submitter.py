#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys


def parse_report(report_path):
    if not os.path.exists(report_path):
        print(f"[-] Error: Report not found at {report_path}", file=sys.stderr)
        sys.exit(1)

    with open(report_path, encoding="utf-8") as f:
        content = f.read()

    # Extraer título y severidad
    title_match = re.search(r"# (.*)", content)
    severity_match = re.search(r"Severity:\s*(\w+)", content)

    title = title_match.group(1).strip() if title_match else "Sovereign Audit Finding"
    severity = severity_match.group(1).strip() if severity_match else "HIGH"

    # Limpiar título de sufijos molestos como "AUDIT REPORT"
    title = re.sub(r"(?i)\s*audit\s*report", "", title).strip()

    return title, severity, content


def build_applescript(contest_id, title, severity, description):
    # Escapar comillas y barras para JavaScript en AppleScript
    js_escaped_title = title.replace('"', '\\"').replace("'", "\\'")
    js_escaped_desc = (
        description.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("'", "\\'")
        .replace("\n", "\\n")
    )

    target_url = f"https://code4rena.com/audits/{contest_id}/submit"

    script = f'''
    tell application "Google Chrome"
        activate
        delay 0.5
        set foundTab to false
        set targetUrl to "{target_url}"
        
        -- Buscar si ya tenemos una pestaña con la URL objetivo
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t starts with "https://code4rena.com" then
                    set URL of t to targetUrl
                    set active tab index of w to (id of t)
                    set index of w to 1
                    set foundTab to true
                    exit repeat
                end if
            end repeat
            if foundTab then exit repeat
        end repeat
        
        -- Si no se encuentra, abrir una nueva pestaña
        if not foundTab then
            if (count of windows) is 0 then
                make new window
            end if
            tell first window to make new tab with properties {{URL:targetUrl}}
        end if
        
        -- Esperar a que la página cargue (espera simple de 3s para Next.js hydration)
        delay 3
        
        -- Ejecutar JS para rellenar los inputs de Code4rena
        tell active tab of first window
            execute javascript "
                (function() {{
                    // Rellenar Título
                    var titleInput = document.querySelector('input[name=\\"title\\"], input[placeholder*=\\"Title\\"], #title, input[type=\\"text\\"]');
                    if (titleInput) {{
                        titleInput.value = '{js_escaped_title}';
                        titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        titleInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                    
                    // Rellenar Descripción
                    var descArea = document.querySelector('textarea[name=\\"description\\"], textarea[name=\\"body\\"], textarea, [contenteditable=\\"true\\"]');
                    if (descArea) {{
                        descArea.value = `{js_escaped_desc}`;
                        descArea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        descArea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                    
                    // Seleccionar Severidad (Búsqueda heurística por texto de etiqueta)
                    var targetSeverity = '{severity}'.toUpperCase();
                    var severityLabels = Array.from(document.querySelectorAll('label, button, span'));
                    var matchLabel = severityLabels.find(el => el.textContent.toUpperCase().includes(targetSeverity) || el.textContent.toUpperCase().includes('HIGH RISK'));
                    if (matchLabel) {{
                        matchLabel.click();
                    }}
                    
                    console.log('CORTEX: Injected findings successfully.');
                }})();
            "
        end tell
    end tell
    '''
    return script


def main():
    parser = argparse.ArgumentParser(
        description="C5-REAL Submitter: Envía hallazgos a Code4rena usando automatización nativa macOS."
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Identificador del concurso en Code4rena (ej: c4-2026-04-layerzero-stellar)",
    )
    parser.add_argument("--report", required=True, help="Ruta al archivo Markdown del reporte")
    args = parser.parse_args()

    print(f"[+] Iniciando C5-REAL Submitter para target: {args.target}")
    title, severity, content = parse_report(args.report)

    print(f"[+] Reporte cargado. Título: '{title}' | Severidad: {severity}")

    # Generar AppleScript
    script_content = build_applescript(args.target, title, severity, content)

    print("[+] Ejecutando AppleScript en Google Chrome...")
    process = subprocess.Popen(
        ["osascript", "-e", script_content],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        print("[∴] C5-REAL: Formulario de Code4rena inyectado en Chrome con éxito.")
        print(
            "[!] Por seguridad termodinámica, revisa los datos y haz clic en 'Submit' manualmente en tu navegador."
        )
    else:
        print(f"[-] Error ejecutando AppleScript: {stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
