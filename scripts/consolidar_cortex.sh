#!/bin/bash
# [C5-REAL] Exergy-Maximized
# Consolidated Cortex-Persist Maintenance Script (Sync + Exergy Singularity Purge)
#
# Runs:
# 1. Sovereign Sync (pull/rebase/test/push)
# 2. Implacable Singularity Purge (cache clean, db vacuum, scratch cleanup)

set -euo pipefail

CWD="/Users/borjafernandezangulo/10_PROJECTS/cortex-persist"
cd "$CWD"

LOG_FILE="$CWD/exergy_singularity.log"
TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

echo "[$TIMESTAMP] [C5-REAL] Starting consolidated cortex-persist maintenance..." >> "$LOG_FILE"

# 1. Run Sovereign Sync (Pull remote changes, run tests, fast push)
echo "🔄 Running Sovereign Sync..."
if ! bash scripts/sovereign_sync.sh; then
    echo "❌ [CONSOLIDAR] Sovereign Sync failed. Aborting further steps." | tee -a "$LOG_FILE"
    exit 1
fi

# 2. Run Implacable Singularity Purge (Clean caches, zcompdump, DB vacuum)
echo "🧹 Running Implacable Singularity Purge..."
if ! .venv/bin/python agent_implacable_omega.py; then
    echo "❌ [CONSOLIDAR] Implacable Singularity Purge failed." | tee -a "$LOG_FILE"
    exit 1
fi

echo "✅ [CONSOLIDAR] Maintenance completed successfully. Exergy at 100%." | tee -a "$LOG_FILE"
