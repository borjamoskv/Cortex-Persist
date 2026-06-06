#!/bin/bash
# C6.6 - Recovery Interrupt Attack
echo "[C5-REAL] Iniciando Recovery Interrupt Attack (C6.6)..."

# Lanzar recuperación en background
cortex daemon --recover &
PID=$!

# Pausa minúscula para garantizar que está en mitad del proceso (lectura WAL/Snapshot)
sleep 0.5

# Asesinato brutal (SIGKILL) - No graceful shutdown
kill -9 $PID
echo "[C5-REAL] Recovery truncado brutalmente (SIGKILL en proceso $PID)."

echo "[C5-REAL] Iniciando segunda pasada de Recovery (Idempotence Check)..."
cortex daemon --recover

# Si esto falla, el recovery mutó el estado sin confirmarlo.
echo "[C5-REAL] Verificar Historical Consistency Index (HCI) post-interrupción."
