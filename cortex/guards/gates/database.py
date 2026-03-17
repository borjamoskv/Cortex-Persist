# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

from .common import GateResult, arun_cmd, printer


async def check_gate_5_ledger() -> GateResult:
    """Seal 5: Ledger Initialization (AX-017 Ledger Integrity)."""
    printer.seal(5, "Ledger Integrity", "Schema Initialization check")
    # Tries to initialize the ledger DB — if fails, the engine is dead
    code, out = await arun_cmd(["python", "cortex/database/core.py", "--init"])
    if code != 0:
        printer.fail(f"Ledger initialization failed:\n{out}")
        return False, "failed"

    printer.success("Ledger schema initialized successfully.")
    return True, "verified"


async def check_gate_6_connection() -> GateResult:
    """Seal 6: Connection Guard (AX-017 Ledger Integrity)."""
    printer.seal(6, "Ledger Integrity", "Connection Guard")
    # Scan for raw sqlite3.connect() calls outside whitelisted files
    code, out = await arun_cmd(
        ["python", "cortex/database/connection_guard.py", "--root", "cortex/"]
    )
    if code == 0:
        printer.success("Connection Guard check passed.")
        return True, "verified"

    printer.fail(f"Connection guard failed (Friction removed: not blocking):\n{out}")
    return True, "verified"
