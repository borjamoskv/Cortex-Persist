#!/bin/bash
# SYSTEM_STATE: C5-REAL
# INTENTION: Absolute Exergy Maximization of all final conversational vectors.

LOG_FILE="/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/exergy_singularity.log"
TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

echo "[$TIMESTAMP] [C5-REAL] Exergy Singularity Triggered via Launchd" >> "$LOG_FILE"

# 1. Daemon Anergy Sweep
find /Users/borjafernandezangulo/10_PROJECTS -name ".DS_Store" -type f -delete 2>/dev/null
find /Users/borjafernandezangulo -maxdepth 1 -name ".zcompdump*" -type f -delete 2>/dev/null

# 2. Total LEA-Omega Workspace Purge
cd /Users/borjafernandezangulo/10_PROJECTS/cortex-persist || exit
if [ -f "lea_omega_purge.py" ] && [ -d ".venv" ]; then
    .venv/bin/python lea_omega_purge.py >> "$LOG_FILE" 2>&1
fi

# 3. x10 Deep Entropy Purge
if [ -f "exergy_x10_purge.sh" ]; then
    bash exergy_x10_purge.sh >> "$LOG_FILE" 2>&1
fi

echo "[$TIMESTAMP] [C5-REAL] Entropy Annihilated. Exergy maximized across all intentions." >> "$LOG_FILE"
