#!/bin/bash
# SOVEREIGN SYNC — State Shadowing Bridge (Ω₁ + Ω₅)
# Sincroniza el handoff.json entre el Mac y el Nodo GCP con latencia <40ms.

GCP_IP=$1
if [ -z "$GCP_IP" ]; then
    echo "❌ Error: Especifica la IP externa del Nodo Antigravity (Ej: ./sovereign_sync.sh 34.1.1.1)."
    exit 1
fi

DEST="borja@$GCP_IP:/home/borja/30_CORTEX"
LOCAL_HANDOFF="./handoff.json"

echo "🔄 Iniciando puente de sincronía con $GCP_IP (Shadowing)..."

while true; do
    # Ω₅: Rsync delta para minimizar transporte de entropía.
    # --inplace para evitar fallos de HUD local por cambios de inodos.
    rsync -azP --inplace -e "ssh -o ConnectTimeout=5" "$LOCAL_HANDOFF" "$DEST/handoff_shadow.json"
    sleep 5
done
