#!/usr/bin/env bash
# [C5-REAL] Exergy-Maximized
# ─── CORTEX Radar Daemon ────────────────────────────────────────────
# Event-driven radar sync and vault scan (Boveda-1 Integration).
# Intended to be run perpetually (24/7) via cron or launchd.
# ────────────────────────────────────────────────────────────────────

set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export HOME="/Users/borjafernandezangulo"
CWD="$HOME/10_PROJECTS/cortex-persist"
cd "$CWD"

LOG_DIR="/tmp"

function run_radar_vault() {
    echo "🔍 [RADAR DAEMON] Inquisitor Vault Scan initiated..."
    VAULT_NAME="radar_vault"
    VAULT_FILE="$HOME/Documents/$VAULT_NAME.sparsebundle"
    MOUNT_POINT="/Volumes/$VAULT_NAME"
    LOG_FILE="$MOUNT_POINT/radar_report_$(date +'%Y%m%d_%H%M%S').log"
    WORKSPACE="$HOME/30_CORTEX"

    # Recuperar llave de Keychain
    VAULT_PASS=$(security find-generic-password -s "$VAULT_NAME" -a "$USER" -w 2>/dev/null || true)
    
    if [ -z "$VAULT_PASS" ]; then
        echo "$(date) - ❌ ERROR: Contraseña de la bóveda no encontrada en el Keychain." >> "$LOG_DIR/radar_daemon_errors.log"
        return 1
    fi

    # Montar bóveda
    echo "$VAULT_PASS" | hdiutil attach "$VAULT_FILE" -stdinpass -mountpoint "$MOUNT_POINT" -quiet

    if ! df -h | grep -q "$MOUNT_POINT"; then
        echo "$(date) - ❌ ERROR: Fallo al montar la bóveda $VAULT_NAME." >> "$LOG_DIR/radar_daemon_errors.log"
        return 1
    fi

    echo "✅ [RADAR DAEMON] Vault mounted. Scanning..."
    if [ -d "$WORKSPACE" ]; then
        cd "$WORKSPACE"
        .venv/bin/python -m cortex.cli radar scan --entropy > "$LOG_FILE" 2>&1 || true
    fi

    # Desmontar de Inmediato
    diskutil eject "$MOUNT_POINT" >/dev/null 2>&1 || true
    echo "✅ [RADAR DAEMON] Vault ejected. Scan complete."
}

function run_auto_radar_sync() {
    echo "📡 [RADAR DAEMON] Auto Radar Graph Sync initiated..."
    cd "$CWD"

    # Run extraction and metric pipelines
    uv run --with feedparser --with networkx --with requests python scripts/extractor_grafo_reputacion.py || true
    uv run --with networkx --with requests python scripts/calculadora_smoke_index.py || true
    uv run python scripts/alpha_extractor_c5.py || true
    
    if [ -f "extensions/mafia-ai-blocker/build_blacklist.py" ]; then
        uv run python extensions/mafia-ai-blocker/build_blacklist.py || true
    fi

    # Sovereign Git Commit
    git add data/reputation_graph/ scripts/ extensions/mafia-ai-blocker/ 2>/dev/null || true
    git commit -m "chore(cortex): auto-radar sync (daemon)" || true
    echo "✅ [RADAR DAEMON] Graph sync and commit complete."
}

# Main Event Loop / Execution
echo "🚀 [RADAR DAEMON] Cycle starting at $(date)"
run_radar_vault || true
run_auto_radar_sync || true
echo "🛑 [RADAR DAEMON] Cycle completed."
