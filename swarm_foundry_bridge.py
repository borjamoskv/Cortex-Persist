import json
import time
import random
import os
import subprocess

# Ruta esclava al Matrix Frontend
MATRIX_STATE_FILE = (
    "/Users/borjafernandezangulo/10_PROJECTS/cortex-exergy-matrix/public/cortex_state.json"
)

LOG_HISTORY = []
CYCLE_COUNT = 0
GLOBAL_YIELD = 0
EXERGY_RATIO = 1.0

# Vectores Físicos
VECTORS = [
    {"id": "bounty", "name": "Code4rena Codebases", "yield": 0, "baseline": 2.5},
    {"id": "mev", "name": "LayerZero Endpoint Fuzz", "yield": 0, "baseline": 1.2},
    {"id": "staking", "name": "Echidna Invariants", "yield": 0, "baseline": 0.8},
]


def add_log(msg, val):
    global LOG_HISTORY
    LOG_HISTORY.append({"id": time.time() + random.random(), "msg": msg, "val": val})
    # Keep only the last 50 logs in memory
    LOG_HISTORY = LOG_HISTORY[-50:]


def flush_ledger(is_running):
    """Atomic write to the React Dashboard"""
    os.makedirs(os.path.dirname(MATRIX_STATE_FILE), exist_ok=True)
    temp_file = MATRIX_STATE_FILE + ".tmp"

    state = {
        "is_running": is_running,
        "cycle_count": CYCLE_COUNT,
        "global_yield": GLOBAL_YIELD,
        "exergy_ratio": EXERGY_RATIO,
        "vectors": VECTORS,
        "logs": LOG_HISTORY,
    }

    with open(temp_file, "w") as f:
        json.dump(state, f)
    os.replace(temp_file, MATRIX_STATE_FILE)


def simulate_foundry_execution():
    """
    Simula el CORTEX P0 Engine levantando Foundry.
    En la Legión Real, aquí haría un subproceso de 'forge test --match-contract CORTEXPoc'
    """
    global CYCLE_COUNT, GLOBAL_YIELD, EXERGY_RATIO, VECTORS

    add_log("FORGE INIT", "[FOUNDRY JIT COMPILER]")
    flush_ledger(True)
    time.sleep(1)

    add_log("AST CRAWLER", "LayerZero Target Acquired")
    flush_ledger(True)

    while True:
        try:
            CYCLE_COUNT += 1
            add_log(f"[CYCLE {CYCLE_COUNT}] MUTATING INVARIANTS", "FUZZING...")

            # Stochastic Extraction Logic (simulando los hallazgos de los agentes)
            cycle_yield = 0
            for v in VECTORS:
                if random.random() > 0.4:
                    gains = v["baseline"] * random.uniform(1.0, 5.0)
                    v["yield"] += gains
                    cycle_yield += gains
                    if gains > 4.0:
                        add_log(f"[{v['name'].upper()}] MARGIN EXPLOIT", f"+{gains:.2f} CXT")

            # Simulated Impact
            EXERGY_RATIO = min(100.0, 1.0 + (CYCLE_COUNT * 0.15))
            GLOBAL_YIELD += cycle_yield * EXERGY_RATIO

            if random.random() < 0.1:
                add_log("⚠️ CRITICAL VULNERABILITY DETECTED", "[REENTRANCY CONFIRMED]")

            flush_ledger(True)
            time.sleep(2.5)  # Frecuencia termodinámica

        except KeyboardInterrupt:
            add_log("CORTEX ENGINE HALTED", "SIGINT")
            flush_ledger(False)
            print("Detenido por señal.")
            break


if __name__ == "__main__":
    print("🔥 ORQUESTADOR OUROBOROS INICIADO. Inyectando Vena Matrix.")
    add_log("SYSTEM BOOT", "OUROBOROS-Ω V1.0")
    flush_ledger(True)
    simulate_foundry_execution()
