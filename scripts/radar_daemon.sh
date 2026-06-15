#!/usr/bin/env bash
# [C5-REAL] GOLPE 2 — CRISTALIZACIÓN v1
# radar_daemon.sh — Unified RADAR-Ω entrypoint
#
# Fusiona:
#   - auto_radar.sh  → --mode sync       (reputation graph + alpha extractor)
#   - radar_cron.sh  → --mode vault-scan (encrypted vault + cortex radar scan)
#
# Usage:
#   radar_daemon.sh --mode sync
#   radar_daemon.sh --mode vault-scan
#   radar_daemon.sh --mode all          (sync first, then vault-scan)
#
# Trigger: launchd plist (LaunchAgent) or cron — single source of truth
# Audit: emits to /tmp/radar_daemon_<date>.log

set -euo pipefail

MODE="${1:-}"
if [[ "$MODE" == "--mode" ]]; then
    MODE="${2:-all}"
fi

LOG_FILE="/tmp/radar_daemon_$(date +'%Y%m%d_%H%M%S').log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[RADAR-Ω] $(date) — mode: ${MODE:-all}"

# ── SYNC MODE ────────────────────────────────────────────────────────────────
run_sync() {
    echo "[RADAR-Ω] Starting sync pass..."

    export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
    export HOME="/Users/borjafernandezangulo"
    local REPO="$HOME/10_PROJECTS/cortex-persist"

    cd "$REPO" || { echo "[ERROR] Repo not found: $REPO"; exit 1; }

    uv run --with feedparser --with networkx --with requests \
        python scripts/extractor_grafo_reputacion.py

    uv run --with networkx --with requests \
        python scripts/calculadora_smoke_index.py

    uv run python scripts/alpha_extractor_c5.py

    uv run python extensions/mafia-ai-blocker/build_blacklist.py

    git add data/reputation_graph/ scripts/ extensions/mafia-ai-blocker/
    git commit -m "chore(cortex): radar-daemon sync $(date +'%Y%m%d_%H%M%S')" || true

    echo "[RADAR-Ω] Sync pass complete."
}

# ── VAULT-SCAN MODE ───────────────────────────────────────────────────────────
run_vault_scan() {
    echo "[RADAR-Ω] Starting vault-scan pass..."

    local VAULT_NAME="radar_vault"
    local VAULT_FILE="$HOME/Documents/$VAULT_NAME.sparsebundle"
    local MOUNT_POINT="/Volumes/$VAULT_NAME"
    local WORKSPACE="$HOME/30_CORTEX"

    VAULT_PASS=$(security find-generic-password -s "$VAULT_NAME" -a "$USER" -w 2>/dev/null || true)

    if [ -z "$VAULT_PASS" ]; then
        echo "[ERROR] Vault password not found in Keychain (key: $VAULT_NAME)"
        echo "$(date) - VAULT_PASS missing" >> /tmp/radar_daemon_errors.log
        exit 1
    fi

    echo "$VAULT_PASS" | hdiutil attach "$VAULT_FILE" \
        -stdinpass -mountpoint "$MOUNT_POINT" -quiet

    if ! df -h | grep -q "$MOUNT_POINT"; then
        echo "[ERROR] Failed to mount vault: $VAULT_NAME"
        echo "$(date) - MOUNT_FAIL" >> /tmp/radar_daemon_errors.log
        exit 1
    fi

    local SCAN_LOG="$MOUNT_POINT/radar_report_$(date +'%Y%m%d_%H%M%S').log"

    cd "$WORKSPACE" || { echo "[ERROR] Workspace not found: $WORKSPACE"; exit 1; }

    .venv/bin/python -m cortex.cli radar scan --entropy > "$SCAN_LOG" 2>&1 || true

    diskutil eject "$MOUNT_POINT" >/dev/null 2>&1 || true

    echo "[RADAR-Ω] Vault-scan complete. Log: $SCAN_LOG"
}

# ── DISPATCH ─────────────────────────────────────────────────────────────────
case "${MODE:-all}" in
    sync)
        run_sync
        ;;
    vault-scan)
        run_vault_scan
        ;;
    all)
        run_sync
        run_vault_scan
        ;;
    *)
        echo "[ERROR] Unknown mode: $MODE"
        echo "Usage: $0 --mode [sync|vault-scan|all]"
        exit 1
        ;;
esac

echo "[RADAR-Ω] $(date) — daemon pass complete. log: $LOG_FILE"
