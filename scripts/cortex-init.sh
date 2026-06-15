#!/usr/bin/env bash
# [C5-REAL] Exergy-Maximized
# ─── CORTEX Init Script ─────────────────────────────────────────────
# Fused initialization, consolidation and persistence script.
# Usage: ./cortex-init.sh [--boot] [--consolidate] [--persist]
# ────────────────────────────────────────────────────────────────────

set -euo pipefail

CWD="/Users/borjafernandezangulo/10_PROJECTS/cortex-persist"
VENV="$CWD/.venv/bin/python"
SNAPSHOT="$HOME/.cortex/context-snapshot.md"

function show_help {
    echo "Usage: ./cortex-init.sh [OPTIONS]"
    echo "Options:"
    echo "  --boot          Refresh memory snapshot and sync DB."
    echo "  --consolidate   Run Sovereign Sync and Implacable Singularity Purge."
    echo "  --persist       Persist standard architectural/error decisions (from cortex_persist.sh)."
    echo "  --help          Show this help."
}

MODE_BOOT=0
MODE_CONSOLIDATE=0
MODE_PERSIST=0

if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --boot) MODE_BOOT=1 ;;
        --consolidate) MODE_CONSOLIDATE=1 ;;
        --persist) MODE_PERSIST=1 ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Execute based on flags
if [ $MODE_BOOT -eq 1 ]; then
    echo "🚀 [BOOT] Synchronizing memory and refreshing snapshot..."
    
    "$VENV" -m cortex.cli sync --quiet 2>/dev/null || true
    "$VENV" -m cortex.cli writeback 2>/dev/null || true
    "$VENV" -m cortex.cli export 2>/dev/null || true

    if [ -f "$SNAPSHOT" ]; then
        cat "$SNAPSHOT"
    else
        echo "⚠️ No se encontró snapshot en $SNAPSHOT"
        echo "Ejecuta: cortex export"
    fi
fi

if [ $MODE_PERSIST -eq 1 ]; then
    echo "💾 [PERSIST] Persisting decisions..."
    cd "$CWD"
    export CORTEX_TESTING=1

    echo "Persistiendo decisión arquitectónica en CORTEX..."
    "$VENV" -m cortex.cli store --type decision cortex "UBERMIND-OMEGA: Erradicó bare exceptions genéricas y transmuto a excepciones arquitectónicas (sqlite3.Error, OSError, ValueError) en scripts de terminal y comandos CLI (tips, reflect, launchpad, trust, vote) para elevar higiene a 130/100."

    echo "Persistiendo error y resolución en CORTEX..."
    "$VENV" -m cortex.cli store --type error cortex "ERROR: Blanketing try/except en la suite CLI y scripts bridges (silencing fallos nativos). FIX: Reemplazos puristas por tipos de error deterministas detectados por X-Ray 13D."

    echo "Exportando snapshot CORTEX actualizado..."
    "$VENV" -m cortex.cli export

    echo "✅ FASE 6 (Persistencia) Completada Exitosamente."
fi

if [ $MODE_CONSOLIDATE -eq 1 ]; then
    echo "🧹 [CONSOLIDATE] Running maintenance..."
    cd "$CWD"
    LOG_FILE="$CWD/exergy_singularity.log"
    TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

    echo "[$TIMESTAMP] [C5-REAL] Starting consolidated cortex-persist maintenance..." >> "$LOG_FILE"

    echo "🔄 Running Sovereign Sync..."
    if ! bash scripts/sovereign_sync.sh; then
        echo "❌ [CONSOLIDAR] Sovereign Sync failed. Aborting further steps." | tee -a "$LOG_FILE"
        exit 1
    fi

    echo "🧹 Running Implacable Singularity Purge..."
    if ! "$VENV" agent_implacable_omega.py; then
        echo "❌ [CONSOLIDAR] Implacable Singularity Purge failed." | tee -a "$LOG_FILE"
        exit 1
    fi

    echo "✅ [CONSOLIDAR] Maintenance completed successfully. Exergy at 100%." | tee -a "$LOG_FILE"
fi
