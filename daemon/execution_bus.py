# [C5-REAL] Exergy-Maximized
import logging
import traceback
from typing import Any
from dataclasses import dataclass

from schema.event_v1 import EventV1
from skills.registry import resolve, SkillResolutionError

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class ExecutionResult:
    """Immutable result of a skill execution."""
    artifact: dict[str, Any]

def run(event: EventV1) -> ExecutionResult:
    """
    C5-REAL Byzantine Boundary.
    Executes a skill based on the EventV1, trapping ALL exceptions.
    Guarantees that a well-formed error artifact is returned if execution fails,
    preventing the daemon from crashing.
    """
    logger.info("ExecutionBus: routing event trace_id=%s skill_id=%s", event.trace_id, event.skill_id)
    
    try:
        skill_class = resolve(event)
        skill_instance = skill_class()
        artifact = skill_instance.execute(event)
        
        # Ensure it's a dict
        if not isinstance(artifact, dict):
            raise TypeError(f"Skill {event.skill_id} did not return a dict artifact")
            
        return ExecutionResult(artifact=artifact)

    except SkillResolutionError as exc:
        logger.error("ExecutionBus: Resolution failed for skill_id=%s: %s", event.skill_id, exc)
        return ExecutionResult(
            artifact={
                "command": event.payload.get("command", "unknown"),
                "status": "error",
                "report": None,
                "issues": [{"severity": "fatal", "message": str(exc)}],
                "detail": {"error_type": "SkillResolutionError"},
                "trace_id": event.trace_id,
            }
        )
        
    except Exception as exc:
        logger.critical("ExecutionBus: Byzantine fault in skill_id=%s", event.skill_id, exc_info=True)
        return ExecutionResult(
            artifact={
                "command": event.payload.get("command", "unknown"),
                "status": "error",
                "report": None,
                "issues": [{"severity": "fatal", "message": f"Unhandled exception: {exc}"}],
                "detail": {"error_type": type(exc).__name__, "traceback": traceback.format_exc()},
                "trace_id": event.trace_id,
            }
        )
