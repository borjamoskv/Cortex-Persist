#!/bin/bash
# ◈ CORTEX-WEALTH-TRIAD LAUNCHER ◈
# Launches Artemis, Hound, and Mercor in parallel.

echo "╔══════════════════════════════════════════════════╗"
echo "║  ∴ THE WEALTH TRIAD — OUROBOROS-∞              ║"
echo "║  Artemis (Silicon) | Hound (Mind) | Mercor (Ops) ║"
echo "╚══════════════════════════════════════════════════╝"

# 1. Start Mercor (Human Intel)
echo "[◈ MERCOR] Background: Sourcing Experts..."
python3 engine/mercor-omega/src/agent.py &
MERCOR_PID=$!

# 2. Start Hound (Cognitive Bridge)
echo "[◈ HOUND] Background: Listening for Signals..."
python3 scripts/agent_hound_omega.py --daemon &
HOUND_PID=$!

# 3. Start Artemis (Main Extraction Engine)
echo "[◈ ARTEMIS] Initializing Engine..."
cd engine/artemis-omega && cargo run --release &
ARTEMIS_PID=$!

# 4. Success State
echo "◈ SWARM DEPLOYED. Monitoring PIDs: $MERCOR_PID, $HOUND_PID, $ARTEMIS_PID"
echo "◈ Status: C5-REAL | Extraction: PENDING"

# Keep script running to monitor children if needed, or exit
# wait $ARTEMIS_PID
