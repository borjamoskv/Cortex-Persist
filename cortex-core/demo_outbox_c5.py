import json
from persistence import HybridPersistenceManager

pm = HybridPersistenceManager()
payload = json.dumps({"finding": "ChaosExplosion", "target_file": "TargetToCorrupt.json"})
pm.l1._conn.execute("INSERT INTO cortex_swarm_queue (agent, payload, status) VALUES (?, ?, ?)", ("VulnerabilityFixer", payload, "pending"))  # pyright: ignore[reportAttributeAccessIssue]
pm.l1._conn.commit()  # pyright: ignore[reportAttributeAccessIssue]
print("Injected ChaosExplosion exploit task into L1 Mempool")
