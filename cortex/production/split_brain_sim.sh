#!/bin/bash
# 5. Split Brain Simulator
# Spawn dos kernels simultáneamente apuntando al mismo ledger para evaluar Lock Contention y Divergencia de estado.
echo "[C5-REAL] Forzando Split-Brain Lock Contention..."
cortex daemon --id node_alpha &
ALPHA_PID=$!

cortex daemon --id node_omega &
OMEGA_PID=$!

sleep 15
echo "[C5-REAL] Deteniendo clúster anómalo..."
kill $ALPHA_PID $OMEGA_PID
echo "[C5-REAL] Split-Brain terminado. Inicia reconciliación y revisa state_divergence."
