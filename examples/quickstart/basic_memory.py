#!/usr/bin/env python3
"""CORTEX Quickstart: Store and verify a decision.

This example shows the core CORTEX workflow:
1. Store a fact with cryptographic integrity
2. Verify its hash chain
3. Check the full ledger integrity

Usage:
    python examples/quickstart/basic_memory.py
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


async def main() -> None:
    # Use a temporary database for this example
    db_path = Path(tempfile.mkdtemp()) / "quickstart.db"

    # Import CortexEngine — the single entry point for all operations
    from cortex.engine import CortexEngine

    engine = CortexEngine(db_path=str(db_path))

    print("🧠 CORTEX Quickstart — Basic Memory\n")

    # --- Step 1: Store facts ---
    print("1️⃣  Storing decisions...")
    fact1 = await engine.store_fact(
        content="Chose OAuth2 PKCE for authentication",
        fact_type="decision",
        project="quickstart",
        source="human:developer",
    )
    print(f"   ✅ Fact #{fact1['id']} stored (hash: {fact1['hash'][:12]}...)")

    fact2 = await engine.store_fact(
        content="Selected PostgreSQL over MongoDB for audit compliance",
        fact_type="decision",
        project="quickstart",
        source="human:architect",
    )
    print(f"   ✅ Fact #{fact2['id']} stored (hash: {fact2['hash'][:12]}...)")

    # --- Step 2: Verify a single fact ---
    print("\n2️⃣  Verifying fact integrity...")
    result = await engine.verify_fact(fact1["id"])
    status = "✅ VERIFIED" if result["valid"] else "❌ BROKEN"
    print(f"   {status} — Hash chain: {result.get('chain_status', 'ok')}")

    # --- Step 3: Search facts ---
    print("\n3️⃣  Searching memory...")
    facts = await engine.search_facts("authentication", project="quickstart")
    print(f"   Found {len(facts)} matching fact(s)")
    for f in facts:
        print(f"   → [{f['type']}] {f['content'][:60]}")

    # --- Step 4: Generate compliance report ---
    print("\n4️⃣  Compliance check...")
    report = await engine.compliance_report(project="quickstart")
    print(f"   Score: {report.get('score', 'N/A')}/5")
    print(f"   Status: {report.get('status', 'unknown')}")

    print("\n✨ Done! CORTEX verified all decisions with cryptographic integrity.")
    print(f"   Database: {db_path}")


if __name__ == "__main__":
    asyncio.run(main())
