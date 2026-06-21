import json
import logging
from pathlib import Path

logger = logging.getLogger("ouroboros.memory")
DATA_DIR = Path("/app/data") if Path("/app").exists() else Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def save_heartbeat(state: dict):
    try:
        with open(DATA_DIR / "heartbeats.jsonl", "a") as f:
            f.write(json.dumps(state) + "\\n")
    except Exception as e:
        logger.error(f"Failed to save heartbeat: {e}")

def save_memory(state: dict, plan: dict, result: str, outcome: str):
    record = {
        "state": state,
        "plan": plan,
        "result": result,
        "outcome": outcome
    }
    try:
        with open(DATA_DIR / "actions.jsonl", "a") as f:
            f.write(json.dumps(record) + "\\n")
        logger.info(f"Action memory saved: {outcome}")
    except Exception as e:
        logger.error(f"Failed to save action memory: {e}")
