# [C5-REAL] Exergy-Maximized
import datetime
import json
import os

LOG_FILE = os.path.expanduser("~/.gemini/config/skills/_metrics/runtime_events.jsonl")


class CortexTelemetry:
    """C5-REAL Runtime Event Logger for CORTEX skills and workflows."""

    def __init__(self, log_path: str = LOG_FILE):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w"):
                pass

    def log_event(
        self,
        session_id: str,
        call_id: str,
        skill: str,
        event_type: str,
        source: str = "unknown",
        duration_ms: int | None = None,
        success: bool | None = None,
        trigger: str = "hook",
        **kwargs,
    ):
        """Logs a single skill execution event with correlation IDs."""
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "call_id": call_id,
            "skill": skill,
            "source": source,
            "event_type": event_type,
            "trigger": trigger,
        }

        if duration_ms is not None:
            entry["duration_ms"] = duration_ms
        if success is not None:
            entry["success"] = success

        entry.update(kwargs)

        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")


telemetry = CortexTelemetry()
