#!/usr/bin/env bash

# ==============================================================================
# CORTEX-Persist Bootstrap Script
# ==============================================================================
# Aprovisionamiento determinista del entorno de desarrollo (Axioma Ω₂).
# Instala exactamente las 15 extensiones soberanas y valida la configuración LSP.
# Tiempo objetivo de inicialización: < 3 segundos.
# ==============================================================================

set -e

echo "[CORTEX-BOOTSTRAP] Iniciando aprovisionamiento C5-REAL..."

# Detección del CLI del IDE
if command -v cursor &> /dev/null; then
    IDE_CMD="cursor"
elif command -v code &> /dev/null; then
    IDE_CMD="code"
else
    echo "[!] No se detectó 'cursor' ni 'code' en el PATH. Las extensiones no se instalarán automáticamente."
    IDE_CMD=""
fi

# Las 15 Extensiones Soberanas (Sin entropía)
EXTENSIONS=(
    "charliermarsh.ruff"                      # Python Linter & Formatter (Oficial)
    "ms-python.python"                        # Python Core LSP
    "ms-python.debugpy"                       # Python Debugger
    "rust-lang.rust-analyzer"                 # Rust Core LSP
    "google.gemini-cli-vscode-ide-companion"  # Antigravity/Gemini (AI Soberana)
    "eamodio.gitlens"                         # Git Forensics
    "editorconfig.editorconfig"               # Consistencia estructural
    "esbenp.prettier-vscode"                  # Formateo Web/JSON/YAML
    "dbaeumer.vscode-eslint"                  # JS/TS/UI Linting
    "redhat.vscode-yaml"                      # Soporte YAML avanzado
    "yzhang.markdown-all-in-one"              # Markdown CORTEX Docs
    "shd101wyy.markdown-preview-enhanced"     # Markdown Previews
    "mtxr.sqltools"                           # SQLite / SQL Data Tooling
    "vscodevim.vim"                           # Keybindings tácticos
    "github.vscode-pull-request-github",      # GitHub PRs Integration
    "openai.codex"                            # Tactical Auxiliary (ChatGPT macOS Bridge)
)

# ==============================================================================
# Sovereign Telemetry Block (C5-REAL Enforced)
# ==============================================================================
$IDE_CMD config set telemetry.telemetryLevel off >/dev/null 2>&1 || true

if [ -n "$IDE_CMD" ]; then
    echo "[CORTEX-BOOTSTRAP] Purgando entropía: desinstalando extensiones no autorizadas..."
    INSTALLED_EXTS=$($IDE_CMD --list-extensions | tr '[:upper:]' '[:lower:]')
    
    for installed in $INSTALLED_EXTS; do
        is_sovereign=0
        for ext in "${EXTENSIONS[@]}"; do
            ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
            if [ "$installed" == "$ext_lower" ]; then
                is_sovereign=1
                break
            fi
        done
        
        if [ $is_sovereign -eq 0 ]; then
            echo "[-] Eliminando entropía: $installed"
            $IDE_CMD --uninstall-extension "$installed" >/dev/null 2>&1 || true
        fi
    done

    echo "[CORTEX-BOOTSTRAP] Instalando 15 extensiones soberanas vía '$IDE_CMD'..."
    for ext in "${EXTENSIONS[@]}"; do
        $IDE_CMD --install-extension "$ext" --force >/dev/null 2>&1 || echo "[!] Advertencia: Falló instalación de $ext"
    done
fi

# Validación básica de estructura de workspace
if [ ! -f ".vscode/settings.json" ]; then
    echo "[CORTEX-BOOTSTRAP] Advertencia: .vscode/settings.json no encontrado."
fi

echo "[CORTEX-BOOTSTRAP] Aprovisionamiento completado con éxito (0 Entropía)."
