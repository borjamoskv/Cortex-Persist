#!/bin/bash

# --- SOVEREIGN LAUNCHPAD v1.0 ---
# Orchestrates the public exposure of the MCP Gateway.

GATEWAY_PORT=8001
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CWD="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "--------------------------------------------------"
echo "∴ SOVEREIGN LAUNCHPAD — Initiating Protocol 12..."
echo "--------------------------------------------------"

# 1. Cleanup existing processes on port 8001
echo "[*] Cleaning up port $GATEWAY_PORT..."
lsof -ti:$GATEWAY_PORT | xargs kill -9 2>/dev/null || true

# 2. Start the Gateway in the background
echo "[*] Booting Gateway (Membrane) on port $GATEWAY_PORT..."
python3 "$CWD/scripts/mcp_saas/gateway.py" &
GW_PID=$!

# 3. Wait for Gateway to be ready
sleep 3

# 4. Start Cloudflare Tunnel
echo "[*] Opening Public Bridge via Cloudflare..."
cloudflared tunnel --url http://localhost:$GATEWAY_PORT > /tmp/cloudflared.log 2>&1 &
TUNNEL_PID=$!

echo "[*] Waiting for tunnel to propagate..."
sleep 8

# 5. Extract Public URL from Cloudflare logs
PUBLIC_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' /tmp/cloudflared.log | head -n 1)

if [ -z "$PUBLIC_URL" ]; then
    echo "[!] ERROR: Failed to retrieve Public URL. Checking logs..."
    cat /tmp/cloudflared.log | tail -n 5
    kill $GW_PID
    kill $TUNNEL_PID
    exit 1
fi

echo "--------------------------------------------------"
echo "🚀 FORGE IS LIVE"
echo "Public Endpoint: $PUBLIC_URL/api/mcp/message"
echo "Gateway PID: $GW_PID"
echo "Tunnel PID: $TUNNEL_PID"
echo "--------------------------------------------------"
echo "Press Ctrl+C to terminate both processes and close the bridge."

# Handle cleanup on exit
trap "kill $GW_PID; kill $TUNNEL_PID; echo '[-] Bridge closed. Exergy flow terminated.'; exit" INT TERM

# Keep script running
wait
