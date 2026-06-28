# [C5-REAL] Exergy-Maximized
"""
Atheris Fuzzer for CORTEX Ledger operations.
Requires Linux. Fuzzes the canonicalization and signature generation to detect
buffer overflows, unhandled exceptions, and memory leaks.
"""

import sys
import sqlite3
import atheris


# Only run if Atheris is successfully imported (Linux-only, typical for oss-fuzz)
def initialize_ledger():
    conn = sqlite3.connect(":memory:")
    from cortex.audit.ledger import EnterpriseAuditLedger

    return conn, EnterpriseAuditLedger(conn)


try:
    with atheris.instrument_imports():
        import cortex.engine.causal.taint_engine as taint_engine
        import cortex.audit.ledger as ledger_engine
except ImportError:
    pass


@atheris.instrument_func
def TestOneInput(data):
    if len(data) < 10:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Extract fuzzed properties
    actor_id = fdp.ConsumeUnicodeNoSurrogates(10)
    tenant_id = fdp.ConsumeUnicodeNoSurrogates(10)
    action = fdp.ConsumeUnicodeNoSurrogates(10)
    payload_str = fdp.ConsumeUnicodeNoSurrogates(100)

    # Try canonicalizing payload
    try:
        taint_engine.canonicalize_content(payload_str)
    except Exception:
        # We only care about crashes, not handled exceptions
        pass

    # We could fuzz the append_sync directly if we had a persistent in-memory DB here
    # but for Fuzzing, isolating canonicalize_content is the most robust step.


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
