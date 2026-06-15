#!/bin/bash
# [DEPRECATED — GOLPE 1 — CRISTALIZACIÓN v1]
# Este wrapper está reemplazado por scripts/sovereign_pre_commit.py (canonical)
#
# Motivo de deprecación:
#   - sovereign_pre_commit.py implementa el mismo flujo con audit trail SQLite
#   - Este .sh no tiene test, no emite audit entry, duplica lógica parcialmente
#
# Acción requerida:
#   .git/hooks/pre-commit → python3 scripts/sovereign_pre_commit.py
#
# Estado: QUARANTINE — eliminar en próximo dead_code_drop pass
# Fecha: 2026-06-15

echo "[DEPRECATED] Use scripts/sovereign_pre_commit.py instead" >&2
echo "Run: python3 scripts/sovereign_pre_commit.py" >&2
exit 1
