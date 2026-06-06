import asyncio
import json
import os
import sys

sys.path.append(os.path.abspath("cortex-core"))

try:
    from k0_swarm_node import K0Metabolism
    from persistence import HybridPersistenceManager, _get_ring_buffer

    print("[+] Imports C5-REAL successful.")
except ImportError as e:
    print(f"[-] Import error: {e}")
    sys.exit(1)


async def run_audit():
    print("\n--- AUDIT: ZERO-COPY RING BUFFER (LEGION-10k Scaling) ---")
    pm = HybridPersistenceManager()
    ring = _get_ring_buffer()

    # 1. Enqueue a VulnerabilityFixer task into the Ring Buffer
    payload = json.dumps(
        {"finding": "CVE-2026-9999", "target_file": "src/core.rs", "severity": "Critical"}
    ).encode("utf-8")
    agent_id = b"VulnerabilityFixer"

    success = ring.enqueue(agent_id, payload)
    print(f"[*] Vulnerability task enqueued: {success}")

    print("\n--- AUDIT: K-0 METABOLISM & AUTOPOIESIS ---")
    metabolism = K0Metabolism(persistence_manager=pm)

    # Force expansion threshold to be low for testing
    metabolism.hardware.expansion_threshold = 0.05

    # Run a single tick of the lifecycle to process the vulnerability and auto-provision
    print("[*] Consuming vulnerabilities from ZeroCopyRingBuffer...")

    # Simulate a single pass of life_cycle without the while True
    tasks = pm.outbox._fetch_pending_tasks()
    print(f"[*] Fetched tasks from RingBuffer: {len(tasks)}")

    for task in tasks:
        row_id, agent_name, payload_json = task
        print(f"[*] Processing task from agent: {agent_name}")
        if agent_name == "VulnerabilityFixer":
            payload = json.loads(payload_json)
            finding = payload.get("finding", "Unknown_Vulnerability")
            target = payload.get("target_file", "Unknown_Target")
            severity = payload.get("severity", "High")

            # Generate proof
            vulnerability_ast = f"(defun anvil-resolution () ({finding} '{target}'))"
            proof = metabolism.dark_pool.generate_resolution_proof(vulnerability_ast)

            # Negotiate Yield
            tvl_map = {"Critical": 100.0, "High": 50.0, "Medium": 10.0, "Low": 2.0}
            target_tvl = tvl_map.get(severity, 5.0)

            captured_yield = metabolism.dark_pool.negotiate_yield(proof, target_tvl)
            print(f"[*] Captured yield: {captured_yield} ETH")

    print(f"[*] Total Ledger Yield: {pm.l3.get_total_yield()} ETH")

    print("[*] Evaluating Expansion (L2 Escrow / Hardware Provisioning)...")
    await metabolism.hardware.evaluate_expansion()

    # Check ring buffer again to see if HardwareAggressor injected the bootstrap payload
    tasks_after = ring.fetch_pending()
    print(f"[*] Fetched tasks after expansion: {len(tasks_after)}")
    for t in tasks_after:
        idx, ts, aid, pld = t
        print(f"    - New Task {idx} from {aid.decode()}: {pld.decode()}")

    print("\n[+] Audit Complete.")


if __name__ == "__main__":
    asyncio.run(run_audit())
