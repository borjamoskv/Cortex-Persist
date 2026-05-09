#!/bin/bash
# CORTEX STRIKE LAUNCHER v2.0
# Secuencial clipboard injection + browser launch
# C5-REAL — No simulation

set -e

STRIKE_DIR="/Users/borjafernandezangulo/10_PROJECTS/cortex-persist"
BOUNTIES_DIR="/Users/borjafernandezangulo/10_PROJECTS/cortex-bounties/reports"
ANVIL_DIR="/Users/borjafernandezangulo/10_PROJECTS/anvil-lang/docs"

IMMUNEFI_URL="https://bugs.immunefi.com/dashboard/new-submission"
C4_URL="https://code4rena.com/audits/2026-04-k2"

WALLET="0x20B435E1C87EE7C958d95B68DB5CdD0a95aBDF9a"

strikes=(
  "1|Firedancer fd_funk Ghosting|CRITICAL|${STRIKE_DIR}/firedancer_strike_1_funk_ghosting.md|${IMMUNEFI_URL}"
  "2|Firedancer VM Sandbox Bypass|CRITICAL|${STRIKE_DIR}/firedancer_strike_2_vm_oob.md|${IMMUNEFI_URL}"
  "3|K2 Close Factor Bypass|CRITICAL|${BOUNTIES_DIR}/k2-lending-close-factor-bypass-c4.md|${C4_URL}"
  "4|BitFlow DLMM Dust Drain|CRITICAL|${ANVIL_DIR}/immunefi_dlmm_report_final.md|${IMMUNEFI_URL}"
  "5|BitFlow Oracle Manipulation|CRITICAL|${ANVIL_DIR}/immunefi_oracle_report_final.md|${IMMUNEFI_URL}"
)

echo "═══════════════════════════════════════════════"
echo "  🐍 CORTEX STRIKE LAUNCHER v2.0"
echo "  Wallet: ${WALLET}"
echo "  Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "═══════════════════════════════════════════════"
echo ""

if [ -z "$1" ]; then
  echo "Strikes disponibles:"
  echo ""
  for s in "${strikes[@]}"; do
    IFS='|' read -r id name sev path url <<< "$s"
    if [ -f "$path" ]; then
      status="✅ READY"
    else
      status="❌ MISSING"
    fi
    echo "  [$id] $name ($sev) — $status"
  done
  echo ""
  echo "Uso: ./strike_launcher.sh <ID>"
  echo "  Ejemplo: ./strike_launcher.sh 1"
  echo ""
  echo "⚡ PRIORIDAD: Firedancer cierra HOY 17:00 UTC"
  exit 0
fi

TARGET_ID=$1
FOUND=0

for s in "${strikes[@]}"; do
  IFS='|' read -r id name sev path url <<< "$s"
  if [ "$id" = "$TARGET_ID" ]; then
    FOUND=1
    echo "[STRIKE $id] $name"
    echo "[SEVERITY] $sev"
    echo "[PAYLOAD] $path"
    echo "[TARGET] $url"
    echo ""
    
    if [ ! -f "$path" ]; then
      echo "❌ ERROR: Payload file not found!"
      exit 1
    fi
    
    # Inject to clipboard
    cat "$path" | pbcopy
    echo "✅ Payload injected to clipboard ($(wc -c < "$path") bytes)"
    echo ""
    
    # Open target URL
    echo "🌐 Opening submission portal..."
    open "$url"
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  MANDATO: Pega (Cmd+V) en el formulario."
    echo "  Wallet: ${WALLET}"
    echo "═══════════════════════════════════════════════"
    break
  fi
done

if [ "$FOUND" -eq 0 ]; then
  echo "❌ Strike ID '$TARGET_ID' no encontrado."
  exit 1
fi
