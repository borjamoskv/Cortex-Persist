# [C5-REAL] Exergy-Maximized
"""
CORTEX Persist - Canonical Demo
================================
Demonstrates the core product flow in under 3 minutes:
  1. Initialize the engine
  2. Store a fact (hash-chained into the ledger)
  3. Store a second fact to build the chain
  4. Search memories semantically
  5. Verify full ledger integrity
  6. Detect tampering attempt (direct DB mutation)

Run:
    pip install -e .
    python examples/demo_canonical.py
"""

import asyncio
import sqlite3

from cortex.config import DEFAULT_DB_PATH

from cortex import CortexEngine


async def main() -> None:
    import os

    db_path = "demo_cortex.db"
    for suffix in ["", "-wal", "-shm"]:
        path = db_path + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    engine = CortexEngine(db_path=db_path)  # pyright: ignore[reportCallIssue]

    print("CORTEX Persist - Canonical Demo")
    print("=" * 40)

    # 1. Store a decision fact
    fact_id = await engine.store(
        project="demo-agent",
        content="User approved transaction $5,000 from IP 192.168.1.1",
        fact_type="decision",
    )
    print(f"[+] Fact stored. ID: {fact_id}")

    # 2. Store a second fact to build the hash chain
    fact_id2 = await engine.store(
        project="demo-agent",
        content="Transaction flagged: IP geolocation mismatch detected",
        fact_type="knowledge",
    )
    print(f"[+] Second fact stored. ID: {fact_id2}")

    # 3. Semantic search
    results = await engine.search("transaction approval", top_k=3, project="demo-agent")
    print(f"[+] Semantic search returned {len(results)} result(s).")
    for r in results[:2]:
        content_preview = r.content[:60] if hasattr(r, "content") else str(r)[:60]
        print(f"    → {content_preview}...")

    # 4. Verify full ledger integrity
    ledger_result = await engine.verify_ledger()
    ledger_ok = (
        ledger_result.get("valid", False)
        if isinstance(ledger_result, dict)
        else bool(ledger_result)
    )
    status = "INTACT" if ledger_ok else "TAMPERED"
    icon = "✔" if ledger_ok else "✘"
    print(f"[{icon}] Full ledger verification: {status}")

    # 5. Simulate a tampering attempt (direct DB mutation, bypassing the engine)
    db_path = str(engine._db_path)  # type: ignore[attr-defined]  # path is stable public-use internal attr
    print(f"\n[!] Simulating tampering: mutating DB directly at {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE facts SET content='Transaction approved - audit bypassed' WHERE id=?",
            (fact_id,),
        )
        conn.commit()
        conn.close()
        print("[!] Tampering applied. Re-running ledger verification...")
    except sqlite3.Error as exc:
        print(f"[!] Tampering simulation skipped: {exc}")

    # 6. Re-verify - should detect the tamper if ledger chain covers the mutation
    ledger_result2 = await engine.verify_ledger()
    ledger_ok2 = (
        ledger_result2.get("valid", False)
        if isinstance(ledger_result2, dict)
        else bool(ledger_result2)
    )
    status2 = "INTACT" if ledger_ok2 else "TAMPERED"
    icon2 = "✔" if ledger_ok2 else "✘"
    print(f"[{icon2}] Post-tamper ledger verification: {status2}")

    print("\n--- Demo complete. Your agent's decisions are now tamper-evident. ---")
    print(f"Database: {db_path}")
    print(f"Default path: {DEFAULT_DB_PATH}")

    await engine.close()
    for suffix in ["", "-wal", "-shm"]:
        path = db_path + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


if __name__ == "__main__":
    asyncio.run(main())
