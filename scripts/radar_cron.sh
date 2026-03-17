#!/usr/bin/env bash

# RADAR-Ω Automation Script (Boveda-1 Integration)
# Se ejecuta de forma perpetua (24/7) vía cron o launchd.

set -e

# ==== DIAGNÓSTICO FÍSICO ====
VAULT_NAME="radar_vault"
VAULT_FILE="$HOME/Documents/$VAULT_NAME.sparsebundle"
MOUNT_POINT="/Volumes/$VAULT_NAME"
LOG_FILE="$MOUNT_POINT/radar_report_$(date +'%Y%m%d_%H%M%S').log"
WORKSPACE="$HOME/30_CORTEX"

# 1. Recuperar la llave desde el Keychain (Zero-PlainText)
# Nota: La primera vez que cron intente esto, macOS podría pedir permiso (UI prompt) si no se configuró el ACL correcto.
# Si se hace vía launchd con plist LaunchAgent, funciona a nivel de sesión de usuario.
VAULT_PASS=$(security find-generic-password -s "$VAULT_NAME" -a "$USER" -w 2>/dev/null || true)

if [ -z "$VAULT_PASS" ]; then
    echo "$(date) - ❌ ERROR: Contraseña de la bóveda no encontrada en el Keychain." >> /tmp/radar_cron_errors.log
    exit 1
fi

# 2. Montar la bóveda en frío temporalmente
echo "$VAULT_PASS" | hdiutil attach "$VAULT_FILE" -stdinpass -mountpoint "$MOUNT_POINT" -quiet

if ! df -h | grep -q "$MOUNT_POINT"; then
    echo "$(date) - ❌ ERROR: Fallo al montar la bóveda $VAULT_NAME." >> /tmp/radar_cron_errors.log
    exit 1
fi

# 3. Escaneo Inquisidor (Banda G y E) -> Cold Storage
cd "$WORKSPACE"
.venv/bin/python -m cortex.cli radar scan --entropy > "$LOG_FILE" 2>&1 || true

# 4. Desmontar de Inmediato (Auto-Eject Protocol)
diskutil eject "$MOUNT_POINT" >/dev/null 2>&1 || true

# (Opcional) Limpiar el pass del portapapeles/memoria
# python3 -c "import os; os.system('pbcopy < /dev/null')"
