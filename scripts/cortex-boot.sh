#!/usr/bin/env bash
# ─── CORTEX Boot Script ─────────────────────────────────────────────
# Refresca el snapshot de memoria y lo imprime para que el agente lea.
# Uso: source cortex-boot.sh o llamar desde workflows.
# ────────────────────────────────────────────────────────────────────

set -euo pipefail

CORTEX_DIR="$HOME/cortex"
VENV="$CORTEX_DIR/.venv/bin/python"
SNAPSHOT="$HOME/.cortex/context-snapshot.md"

# 1. Sync: JSON → DB (por si hay cambios recientes)
"$VENV" -m cortex.cli sync --quiet 2>/dev/null || true

# 2. Write-back: DB → JSON (por si CORTEX tiene datos nuevos)
"$VENV" -m cortex.cli writeback 2>/dev/null || true

# 3. Export: DB → Snapshot markdown
"$VENV" -m cortex.cli export 2>/dev/null || true

# 4. Imprimir snapshot para ingestión
if [ -f "$SNAPSHOT" ]; then
    cat "$SNAPSHOT"
else
    echo "⚠️ No se encontró snapshot en $SNAPSHOT"
    echo "Ejecuta: cortex export"
fi
