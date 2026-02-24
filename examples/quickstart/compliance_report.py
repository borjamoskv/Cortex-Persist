#!/usr/bin/env python3
"""CORTEX Quickstart: EU AI Act Compliance Report.

Demonstrates how to generate a compliance report that satisfies
EU AI Act Article 12 requirements for logging and traceability.

Usage:
    python examples/quickstart/compliance_report.py
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


async def main() -> None:
    db_path = Path(tempfile.mkdtemp()) / "compliance.db"

    from cortex.engine import CortexEngine

    engine = CortexEngine(db_path=str(db_path))

    print("📋 CORTEX Quickstart — EU AI Act Compliance Report\n")

    # --- Step 1: Simulate an agent's decision history ---
    print("1️⃣  Simulating agent decision history...\n")

    decisions = [
        ("decision", "Approved loan application #443 — risk score 0.23"),
        ("decision", "Rejected application #444 — income verification failed"),
        ("knowledge", "Risk model v2.1 deployed — AUC 0.94 on validation set"),
        ("error", "Timeout on credit bureau API — retried 3x, succeeded"),
        ("decision", "Approved application #445 — manual review flagged"),
    ]

    for fact_type, content in decisions:
        await engine.store_fact(
            content=content,
            fact_type=fact_type,
            project="fintech-agent",
            source="agent:loan-processor",
        )
        print(f"   📝 [{fact_type}] {content[:60]}")

    # --- Step 2: Generate compliance report ---
    print("\n2️⃣  Generating EU AI Act compliance report...\n")
    report = await engine.compliance_report(project="fintech-agent")

    print(f"   🏛️  EU AI Act Article 12 Compliance")
    print(f"   {'=' * 40}")
    print(f"   Score:         {report.get('score', 'N/A')}/5")
    print(f"   Status:        {report.get('status', 'unknown')}")
    print(f"   Total Facts:   {report.get('total_facts', 0)}")
    print(f"   Verified:      {report.get('verified_count', 0)}")

    checks = report.get("checks", {})
    if checks:
        print(f"\n   Requirements:")
        for check, passed in checks.items():
            icon = "✅" if passed else "❌"
            print(f"     {icon} {check}")

    # --- Step 3: Verify data integrity ---
    print(f"\n3️⃣  Verifying ledger integrity...")
    integrity = await engine.verify_integrity(project="fintech-agent")
    icon = "✅" if integrity.get("valid", False) else "❌"
    print(f"   {icon} Ledger: {integrity.get('status', 'unknown')}")
    if "merkle_root" in integrity:
        print(f"   🌳 Merkle root: {integrity['merkle_root'][:16]}...")

    print("\n✨ Compliance report ready for regulatory submission.")
    print("   All decisions are hash-chained and Merkle-sealed.")


if __name__ == "__main__":
    asyncio.run(main())
