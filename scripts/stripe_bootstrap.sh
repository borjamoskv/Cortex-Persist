#!/usr/bin/env bash
# [C5-REAL] Exergy-Maximized
# Stripe Automated Provisioning Protocol

set -e

echo "[+] Starting Stripe provisioning..."

if ! command -v stripe &> /dev/null; then
    echo "[!] Stripe CLI not found. Install it first: brew install stripe/stripe-cli/stripe"
    exit 1
fi

echo "[+] Authenticating with Stripe..."
stripe login

echo "[+] Creating 'Pro' Plan Product..."
PRO_PRODUCT_ID=$(stripe products create --name "CORTEX Pro" --description "Sovereign AI Access" -d "default_price_data[currency]"="usd" -d "default_price_data[unit_amount]"=9900 -d "default_price_data[recurring][interval]"="month" | grep '"id": "prod_' | awk -F'"' '{print $4}')
PRO_PRICE_ID=$(stripe prices list --product "$PRO_PRODUCT_ID" --limit 1 | grep '"id": "price_' | awk -F'"' '{print $4}')

echo "[+] Creating 'Team' Plan Product..."
TEAM_PRODUCT_ID=$(stripe products create --name "CORTEX Team" --description "Sovereign Swarm Access" -d "default_price_data[currency]"="usd" -d "default_price_data[unit_amount]"=29900 -d "default_price_data[recurring][interval]"="month" | grep '"id": "prod_' | awk -F'"' '{print $4}')
TEAM_PRICE_ID=$(stripe prices list --product "$TEAM_PRODUCT_ID" --limit 1 | grep '"id": "price_' | awk -F'"' '{print $4}')

echo "======================================"
echo "PROVISIONING COMPLETE."
echo "Pro Price ID:  $PRO_PRICE_ID"
echo "Team Price ID: $TEAM_PRICE_ID"
echo "======================================"
echo "Update your .env file with the following STRIPE_PRICE_TABLE:"
echo "STRIPE_PRICE_TABLE='{\"pro\": \"$PRO_PRICE_ID\", \"team\": \"$TEAM_PRICE_ID\"}'"
echo ""
echo "Now run 'stripe listen --forward-to localhost:8000/v1/stripe/webhook' to get your STRIPE_WEBHOOK_SECRET."
