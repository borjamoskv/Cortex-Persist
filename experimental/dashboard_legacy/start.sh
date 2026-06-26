#!/bin/bash
# ∴ CORTEX-PERSIST: Unified Startup Script
# Industrial Noir 2026 Production Protocol (Ω6-Execution)

echo "∴ Initiating CORTEX-PERSIST Production Protocol..."

# 1. UI Build Check
if [ ! -d "ui/dist" ]; then
    echo "[!] UI distribution not found. Building now..."
    cd ui && npm install && npm run build && cd ..
fi

# 2. Environment Setup
export CORTEX_ENV=production
export GEMINI_API_KEY="AIzaSyBKnb8fq2rTqj0wQrXXBbqTo0Qz-iicyuE"
export PATH=$PATH:/usr/local/bin

# 3. Process Management
# We kill any existing processes on port 8000
echo "[*] Clearing potential entropy on :8000..."
lsof -ti :8000 | xargs kill -9 2>/dev/null

# 4. Launch Unified Server (API + UI)
echo "[✓] Launching Unified Server..."
python3 scripts/api.py &

# 5. Launch Orchestrator (if not already managed by LaunchAgent)
# Note: In a full production setup, this is handled by launchd
# but for manual start, we trigger it here if requested.
if [ "$1" == "--with-orchestrator" ]; then
    echo "[✓] Launching Background Orchestrator..."
    python3 scripts/orchestrator.py &
fi

echo "∴ CORTEX-PERSIST is now operational at http://localhost:8000"
wait
