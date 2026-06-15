# [C5-REAL] Exergy-Maximized
import logging
import traceback
import json
import os
from typing import Any
from dataclasses import dataclass

from schema.event_v1 import EventV1
from skills.registry import resolve, SkillResolutionError

logger = logging.getLogger(__name__)

def _sign_artifact(event: EventV1, artifact: dict[str, Any]) -> dict[str, Any]:
    """Ouroboros Auto-Healing: Cryptographically seal the execution artifact."""
    if os.environ.get("CORTEX_NO_TAINT_ENFORCE") == "1":
        return artifact

    priv_b64 = None
    if not os.environ.get("CORTEX_TESTING"):
        try:
            import keyring
            priv_b64 = keyring.get_password("cortex_v6", "ed25519_private_key")
        except Exception:
            pass

    if not priv_b64:
        priv_b64 = os.environ.get("CORTEX_ED25519_PRIVATE_KEY")

    if priv_b64:
        from cortex.engine.causal.taint_engine import generate_secure_taint_token
        try:
            content = json.dumps(artifact, sort_keys=True, separators=(',', ':'))
            token = generate_secure_taint_token(
                agent_id=event.source,
                session_id=event.trace_id,
                content=content,
                private_key_b64=priv_b64,
            )
            artifact["cortex_taint"] = token
        except Exception as e:
            logger.warning("ExecutionBus: Failed to sign execution artifact: %s", e)
    return artifact

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
            
        artifact = _sign_artifact(event, artifact)
        return ExecutionResult(artifact=artifact)

    except SkillResolutionError as exc:
        logger.error("ExecutionBus: Resolution failed for skill_id=%s: %s", event.skill_id, exc)
        err_artifact = {
            "command": event.payload.get("command", "unknown"),
            "status": "error",
            "report": None,
            "issues": [{"severity": "fatal", "message": str(exc)}],
            "detail": {"error_type": "SkillResolutionError"},
            "trace_id": event.trace_id,
        }
        return ExecutionResult(artifact=_sign_artifact(event, err_artifact))
        
    except Exception as exc:
        logger.critical("ExecutionBus: Byzantine fault in skill_id=%s", event.skill_id, exc_info=True)
        err_artifact = {
            "command": event.payload.get("command", "unknown"),
            "status": "error",
            "report": None,
            "issues": [{"severity": "fatal", "message": f"Unhandled exception: {exc}"}],
            "detail": {"error_type": type(exc).__name__, "traceback": traceback.format_exc()},
            "trace_id": event.trace_id,
        }
        return ExecutionResult(artifact=_sign_artifact(event, err_artifact))
