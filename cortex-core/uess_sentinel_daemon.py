import os
import json
import time
import logging
from typing import Dict, Any

logger = logging.getLogger("cortex.sentinel_daemon")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class DriftVectorField:
    def __init__(self):
        self.semantic_drift = 0.0
        self.goal_deviation = 0.0
        self.entropy_growth = 0.0
        self.contradiction_index = 0.0
        self.identity_coherence = 1.0

    def as_dict(self) -> Dict[str, float]:
        return {
            "semantic_drift": self.semantic_drift,
            "goal_deviation": self.goal_deviation,
            "entropy_growth": self.entropy_growth,
            "contradiction_index": self.contradiction_index,
            "identity_coherence": self.identity_coherence
        }

class UESSSentinelDaemon:
    """
    C5-REAL Sentinel DAEMON.
    Persistent observer mapping the AOF event log.
    Calculates the Drift Vector Field (DVF) to prevent semantic inflation
    and enforce identity coherence across the Swarm Runtime.
    """
    def __init__(self, log_path: str = "cortex_event_aof.jsonl"):
        self.log_path = log_path
        self.dvf = DriftVectorField()
        self.last_processed_line = 0
        self.last_entropy = 0.0

    def parse_event(self, event: Dict[str, Any]):
        """Modulates the DVF based on event payloads."""
        event_type = event.get("type")
        payload = event.get("payload", {})

        if event_type == "SWARM_TICK":
            current_entropy = payload.get("global_entropy", 0.0)
            # Calculate entropy velocity
            delta = current_entropy - self.last_entropy
            self.dvf.entropy_growth = (self.dvf.entropy_growth * 0.9) + (delta * 0.1)
            self.last_entropy = current_entropy

            # High entropy correlates with goal deviation
            if current_entropy > 0.8:
                self.dvf.goal_deviation = min(1.0, self.dvf.goal_deviation + 0.05)
            else:
                self.dvf.goal_deviation = max(0.0, self.dvf.goal_deviation - 0.01)

        elif event_type == "AST_MUTATE":
            status = payload.get("status")
            if status == "rejected":
                self.dvf.contradiction_index = min(1.0, self.dvf.contradiction_index + 0.1)
                self.dvf.identity_coherence = max(0.0, self.dvf.identity_coherence - 0.05)
            elif status == "success":
                self.dvf.semantic_drift = min(1.0, self.dvf.semantic_drift + 0.02)
                # Successful mutation restores coherence
                self.dvf.identity_coherence = min(1.0, self.dvf.identity_coherence + 0.02)

    def trigger_repair(self):
        """Autonomic reflex if DVF bounds are breached."""
        if self.dvf.identity_coherence < 0.5:
            logger.critical("🚨 IDENTITY COHERENCE COLLAPSE DETECTED. Triggering Ouroboros Repair.")
            # In a full deployment, this triggers Vector 6 (Ouroboros Rewrite)
            self.dvf.identity_coherence = 1.0
            self.dvf.contradiction_index = 0.0
            logger.info("Repair dispatched. DVF reset.")

    def run_cycle(self):
        """Scans the event AOF and updates the global DVF metric."""
        if not os.path.exists(self.log_path):
            return

        new_lines_read = 0
        with open(self.log_path, "r") as f:
            for i, line in enumerate(f):
                if i < self.last_processed_line:
                    continue
                try:
                    event = json.loads(line)
                    self.parse_event(event)
                    new_lines_read += 1
                except json.JSONDecodeError:
                    continue
            self.last_processed_line += new_lines_read

        if new_lines_read > 0:
            logger.info(f"DVF State Updated. Lines parsed: {new_lines_read}")
            logger.info(f"DVF Metrics: {self.dvf.as_dict()}")
            self.trigger_repair()

if __name__ == "__main__":
    daemon = UESSSentinelDaemon()
    # Simulated persistent daemon loop
    logger.info("Starting UESS Sentinel DAEMON. Monitoring event bus...")
    for _ in range(5):
        daemon.run_cycle()
        time.sleep(1)
