#!/bin/bash
# ∴ CORTEX VANGUARD: Autonomous Strike Launcher
# Industrial Noir 2026 Production Protocol (Ω6-Execution)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
LOG_FILE="$SCRIPT_DIR/vanguard.log"

echo "∴ Initiating VANGUARD-OMEGA Background Strike..."
echo "  Log target: $LOG_FILE"

# 1. Kill existing daemon instances
pkill -f cortex_vanguard_daemon.py 2>/dev/null

# 2. Launch in background with proper descriptors (Unbuffered)
export PYTHONUNBUFFERED=1
nohup python3 "$SCRIPT_DIR/cortex_vanguard_daemon.py" > "$LOG_FILE" 2>&1 &

DAEMON_PID=$!

if ps -p $DAEMON_PID > /dev/null; then
    echo "  [✓] VANGUARD Active (PID: $DAEMON_PID)"
    echo "  Status: C5-REAL | Extraction: PULSING"
else
    echo "  [✗] Startup Failed. Check $LOG_FILE"
    exit 1
fi

echo "∴ Strike persistent. Execute 'tail -f $LOG_FILE' for real-time telemetry."
