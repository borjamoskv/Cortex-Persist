import time
import asyncio
from persistence import enqueue_swarm_task, OutboxDaemon

async def main():
    daemon = OutboxDaemon()
    daemon.start_guardian()
    
    # 1. Enqueue an EXA-LISP task directly to the ZeroCopyRingBuffer
    print("[TEST] Enqueuing EXA-LISP Quantum Task to Ring Buffer...")
    payload = {
        "type": "EXA_LISP",
        "code": "(with-exergy-limit 3000j (q-let (invoke-skill capital_extractor_omega CapitalExtractorOmegaSkill) (invoke-skill capital_extractor_omega CapitalExtractorOmegaSkill)))",
        "exergy_limit": 3000
    }
    
    enqueue_swarm_task("agent-omega", payload)
    
    # 2. Let the OutboxDaemon process it
    print("[TEST] Waiting for Daemon to drain...")
    await asyncio.sleep(2)
    
    # 3. Print the results from the DB to verify ledger anchoring
    from persistence import _get_local_conn, DB_PATH
    conn = _get_local_conn(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT action, yield_amount, timestamp FROM ledger_records ORDER BY timestamp DESC LIMIT 5")
    rows = c.fetchall()
    print("\n[TEST] Ledger state after execution:")
    for r in rows:
        print(f"  {r[2]} | {r[0]} | Cost: {r[1]}j")
    
if __name__ == "__main__":
    asyncio.run(main())
