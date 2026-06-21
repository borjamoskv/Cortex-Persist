# [C5-REAL] Exergy-Maximized
import json
import os
import random
from datetime import datetime

LOG = os.path.expanduser("~/.gemini/config/skills/_metrics/cronos_memory.jsonl")

# High throughput / low stability: memory_reconciliation
# Low throughput / high stability: adversarial_simulation
# High throughput / high stability: cron_health_check
# Medium/Medium: vector_compaction
# Fast but mediocre: ingest_pipeline

profiles = {
    "memory_reconciliation": {
        "runs": 10,
        "runtime_mean": 1.5,
        "outcome_mean": 0.5,
        "outcome_std": 0.4,
    },
    "adversarial_simulation": {
        "runs": 10,
        "runtime_mean": 45.0,
        "outcome_mean": 0.95,
        "outcome_std": 0.05,
    },
    "cron_health_check": {
        "runs": 10,
        "runtime_mean": 2.0,
        "outcome_mean": 0.95,
        "outcome_std": 0.05,
    },
    "vector_compaction": {
        "runs": 10,
        "runtime_mean": 15.0,
        "outcome_mean": 0.7,
        "outcome_std": 0.1,
    },
    "ingest_pipeline": {"runs": 10, "runtime_mean": 4.0, "outcome_mean": 0.6, "outcome_std": 0.1},
}

records = []
for wf, p in profiles.items():
    for i in range(p["runs"]):
        # Add random noise
        runtime = max(0.5, random.gauss(p["runtime_mean"], p["runtime_mean"] * 0.2))
        outcome = min(1.0, max(0.1, random.gauss(p["outcome_mean"], p["outcome_std"])))
        exergy_score = outcome / runtime

        # Artificial bad run for counterfactual test:
        # On run 5, adversarial_simulation gets a terrible outcome, but the scheduler still prefers it over memory_reconciliation?
        # Actually, if we just generate history, the prediction engine will use the EMA.

        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": f"mock_{wf}_{i}",
            "workflow": wf,
            "state": "COMPLETED",
            "execution_score": 15.0,
            "planned_minutes": p["runtime_mean"],
            "actual_minutes": runtime,
            "deviation_minutes": runtime - p["runtime_mean"],
            "outcome_score": outcome,
            "exergy_score": exergy_score,
            "exergy_yield": (p["runtime_mean"] - runtime) * outcome,
            "success": True,
            "artifacts": 0,
            "tool_calls": 5,
        }
        records.append(record)

# Append to log
with open(LOG, "a", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")

print(f"Injected {len(records)} mock runs into CRONOS.")
