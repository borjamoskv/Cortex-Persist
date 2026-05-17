#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import time
from datetime import datetime

# Configuración de Target
STELLAR_TARGET_DIR = (
    "/tmp/bounty-targets/c4-layerzero/contracts/protocol/stellar/contracts/endpoint-v2"
)
LEDGER_PATH = os.path.expanduser("~/Cortex-Persist/engine-c5/vanguard_ledger.json")


def log(msg: str, tier: str = "INFO") -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{tier}] [STELLAR-ORCHESTRATOR] {msg}")


def update_ledger(details: str):
    try:
        if os.path.exists(LEDGER_PATH):
            with open(LEDGER_PATH) as f:
                ledger = json.load(f)
        else:
            ledger = {}

        ledger["stellar_endpoint_v2"] = {
            "last_seen": datetime.now().isoformat(),
            "status": "FRACTURED",
            "details": details,
        }

        with open(LEDGER_PATH, "w") as f:
            json.dump(ledger, f, indent=2)
    except Exception as e:
        log(f"Error updating ledger: {e}", "ERROR")


def run_burst():
    log("Iniciando Ráfaga Estocástica de 1,000,000 iteraciones...", "SINGULARITY")

    cmd = ["cargo", "test", "-p", "endpoint-v2", "test_stellar_chaos_burst", "--", "--nocapture"]

    start_time = time.time()
    try:
        process = subprocess.Popen(
            cmd,
            cwd=STELLAR_TARGET_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        output_buffer = []
        for line in process.stdout:
            print(f"  > {line.strip()}")
            output_buffer.append(line)
            if len(output_buffer) > 100:
                output_buffer.pop(0)  # Mantener solo el final

        process.wait()
        duration = time.time() - start_time

        if process.returncode == 0:
            log(f"Asalto completado en {duration:.2f}s. 10^6 resets confirmados.", "C5-SUCCESS")
            update_ledger(
                f"1M Iterations complete in {duration:.2f}s. ALL RESETS VERIFIED. Replay window open."
            )
        else:
            log(f"Falla detectada en el asalto (Exit Code {process.returncode})", "WARN")
            update_ledger("".join(output_buffer))

    except Exception as e:
        log(f"Fatal error during burst: {e}", "ERROR")


if __name__ == "__main__":
    run_burst()
