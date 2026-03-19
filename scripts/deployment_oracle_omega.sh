#!/usr/bin/env bash
# deployment-oracle-omega wrapper
# Runs ship_gate.py → blocks or proceeds to deploy.
set -euo pipefail

REPO="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
GATE_JSON="$(mktemp)"

echo "🔮 deployment-oracle-omega: evaluating ${REPO}..."

python3 "$REPO/scripts/ship_gate.py" "$REPO" | tee "$GATE_JSON"

OK="$(python3 - "$GATE_JSON" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)
print("1" if data.get("ok") else "0")
PY
)"

rm -f "$GATE_JSON"

if [[ "$OK" != "1" ]]; then
    echo ""
    echo "🔴 DEPLOYMENT BLOCKED BY deployment-oracle-omega"
    echo "   Fix all FAIL checks above before deploying."
    exit 2
fi

echo ""
echo "🟢 deployment-oracle-omega: GATE PASS — proceeding to deploy."

# If vanguard-deployment-omega.sh exists, chain into it
if [[ -x "$REPO/scripts/vanguard-deployment-omega.sh" ]]; then
    exec "$REPO/scripts/vanguard-deployment-omega.sh" "$@"
else
    echo "⚠️  No vanguard-deployment-omega.sh found. Gate passed but no deploy target configured."
    echo "   Create scripts/vanguard-deployment-omega.sh or pass a deploy command."
    exit 0
fi
