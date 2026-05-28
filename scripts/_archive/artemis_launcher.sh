#!/bin/bash
# ∴ CORTEX-ARTEMIS: Sovereign MEV Launcher v1.0
# Industrial Noir 2026 Production Protocol (Ω6-Execution)

echo "∴ Initiating CORTEX-ARTEMIS Production Protocol..."

PROJECT_ROOT=$(pwd)
ARTEMIS_BIN="$PROJECT_ROOT/engine/artemis-omega-base/target/release/artemis"

if [ ! -f "$ARTEMIS_BIN" ]; then
    echo "[!] Artemis binary not found at $ARTEMIS_BIN. Use cargo build --release first."
    exit 1
fi

# 1. Environment Setup
export RUST_LOG=info
export ETH_RPC_URL="https://cloudflare-eth.com" # Example, user should update to low-latency RPC
export PRIVATE_KEY="REDACTED" # Injected at runtime or pulled from secure env

# 2. Launch Strategy
echo "[✓] Launching Artemis Engine (Headless)..."
# We run it in the background with nohup to ensure it persists after session close
nohup "$ARTEMIS_BIN" > "$PROJECT_ROOT/data/artemis_yield.log" 2>&1 &

echo "[✓] Artemis is now extracting yield. Logs at data/artemis_yield.log"
