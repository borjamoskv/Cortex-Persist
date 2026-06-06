#!/bin/bash
# CORTEX CLOUD (Managed API + Stripe) Deployment
# Reality Level: C5-REAL
# Pre-requisites: Vercel CLI installed, Turso CLI installed, Stripe configured.

set -e

echo "============================================================"
echo "⚡ CORTEX CLOUD TOPOLOGY INIT (Managed API + Stripe)"
echo "============================================================"
echo "Reality Level: C5-REAL"

if ! command -v vercel &> /dev/null
then
    echo "[!] Error: vercel CLI could not be found. Install via 'npm i -g vercel'."
    exit 1
fi

echo "[1/4] Verifying Environment Configurations..."
if [ -z "$STRIPE_SECRET_KEY" ]; then
    echo "⚠️ Warning: STRIPE_SECRET_KEY is not set in environment."
fi

if [ -z "$TURSO_DATABASE_URL" ]; then
    echo "⚠️ Warning: TURSO_DATABASE_URL is not set. Cortex will default to local SQLite on serverless!"
fi

echo "[2/4] Validating Vercel Configuration..."
if [ ! -f "vercel.json" ]; then
    echo "[!] Error: vercel.json not found."
    exit 1
fi
echo "✓ vercel.json detected."

echo "[3/4] Validating API Dependencies..."
if [ ! -f "api/requirements.txt" ]; then
    echo "[!] Error: api/requirements.txt not found."
    exit 1
fi
echo "✓ API requirements detected."

echo "[4/4] Deploying Cortex Cloud..."
echo "Executing: vercel --prod --archive=tgz"
vercel --prod --archive=tgz

echo "============================================================"
echo "✓ Cortex Cloud (Managed API) Deployment Initiated."
echo "============================================================"
