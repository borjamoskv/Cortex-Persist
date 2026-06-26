#!/bin/zsh
# C5-REAL: IGNITION PROTOCOL
# Ejecuta esta secuencia para enlazar el proof harness al exterior. Cero fricción.

echo "[MOSKV-1] Validando entropía de red..."
if ! gh auth status &>/dev/null; then
    echo "[MOSKV-1] Token caducado. Restaura tu soberanía:"
    gh auth login --web
fi

echo "[MOSKV-1] Forjando repositorio remoto..."
gh repo create babylon-60 --private --source=. --remote=origin --push || git push -u origin master

echo "[MOSKV-1] BABYLON-60 En línea."
