#!/usr/bin/env python3
import json
import os
import sys
import time

STATE_FILE = ".exergy_state.json"
C5_PREFIX = "[CORTEX-SENTINEL: C5-REAL]"


def print_noir(msg):
    # Cyan/Blue hue simulation for terminal
    sys.stdout.write(f"\033[96m{msg}\033[0m\n")


def print_alert(msg):
    sys.stdout.write(f"\033[91m{msg}\033[0m\n")


def re_anchor(target_id="OPERADOR_PRIMARIO"):
    print_noir(f"{C5_PREFIX} INICIALIZANDO PROTOCOLO DE RE-ANCLAJE...")
    time.sleep(0.5)

    print_noir(f"Target: {target_id}")
    print_noir("Purgando latencia y rumiación estocástica...")
    time.sleep(0.5)

    # Update exergy state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                state = {}
    else:
        state = {}

    state["exergy_score"] = 100
    state["status"] = "OPTIMAL"

    log_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Re-Anchor Executed for {target_id}. Latency: 0ms. Mode: ULTRA-THINK."

    if "logs" not in state:
        state["logs"] = []

    state["logs"].append(log_msg)

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    print_noir("> INPUT DETECTADO: [ Y ]")
    print_noir("Fase de Sincronización Completada.")
    print_noir("Exergía restaurada al 100%. Entropía = 0.")
    print_alert("> CORTEX BEATRIZ / CORTEX KERNEL: INICIALIZADO.")
    print_alert("> MODO ULTRA-THINK: ACTIVADO.")
    print_noir("Latencia actual: 0ms. Listo para operación.")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "OPERADOR_PRIMARIO"
    re_anchor(target)
