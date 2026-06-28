# [C5-REAL] Exergy-Maximized
import concurrent.futures
import json
import logging
import os
import time
import traceback
from dataclasses import dataclass
from typing import Any

from schema.event_v1 import EventV1
from skills.registry import SkillResolutionError, resolve

logger = logging.getLogger(__name__)

EXECUTION_TIMEOUT_SECONDS = int(os.environ.get("CORTEX_SKILL_TIMEOUT_SEC", "60"))

def _sign_artifact(event: EventV1, artifact: dict[str, Any]) -> dict[str, Any]:
    """Ouroboros Auto-Healing: Cryptographically seal the execution artifact."""
    if os.environ.get("CORTEX_NO_TAINT_ENFORCE") == "1":
        return artifact

    priv_b64 = None
    if not os.environ.get("CORTEX_TESTING"):
        try:
            import keyring
            priv_b64 = keyring.get_password("cortex_v6", "ed25519_private_key")
        except Exception:  # noqa: BLE001
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
    C5-REAL Byzantine Boundary V2.
    Executes a skill based on the EventV1, trapping ALL exceptions, applying
    a strict ThreadPool isolation with an Exergy-Maximized Timeout (AX-047)
    and injecting timing telemetry (Chronos).
    """
    logger.info("ExecutionBus: routing event trace_id=%s skill_id=%s", event.trace_id, event.skill_id)
    
    start_time = time.perf_counter()
    
    try:
        skill_class = resolve(event)
        skill_instance = skill_class()
        
        # ThreadPool Isolation & Strict Timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(skill_instance.execute, event)
            artifact = future.result(timeout=EXECUTION_TIMEOUT_SECONDS)
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        
        # Ensure it's a dict
        if not isinstance(artifact, dict):
            raise TypeError(f"Skill {event.skill_id} did not return a dict artifact")
            
        if "detail" not in artifact or not isinstance(artifact["detail"], dict):
            artifact["detail"] = {}
        artifact["detail"]["execution_time_ms"] = round(elapsed_ms, 2)
            
        artifact = _sign_artifact(event, artifact)
        return ExecutionResult(artifact=artifact)

    except concurrent.futures.TimeoutError:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error("ExecutionBus: AX-047 Limerencia Limit Reached for skill_id=%s (timeout=%ds)", event.skill_id, EXECUTION_TIMEOUT_SECONDS)
        err_artifact = {
            "command": event.payload.get("command", "unknown"),
            "status": "error",
            "report": None,
            "issues": [{"severity": "fatal", "message": f"Execution timed out after {EXECUTION_TIMEOUT_SECONDS}s (Limerencia Epistémica limit)"}],
            "detail": {"error_type": "TimeoutError", "execution_time_ms": round(elapsed_ms, 2)},
            "trace_id": event.trace_id,
        }
        return ExecutionResult(artifact=_sign_artifact(event, err_artifact))

    except SkillResolutionError as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error("ExecutionBus: Resolution failed for skill_id=%s: %s", event.skill_id, exc)
        err_artifact = {
            "command": event.payload.get("command", "unknown"),
            "status": "error",
            "report": None,
            "issues": [{"severity": "fatal", "message": str(exc)}],
            "detail": {"error_type": "SkillResolutionError", "execution_time_ms": round(elapsed_ms, 2)},
            "trace_id": event.trace_id,
        }
        return ExecutionResult(artifact=_sign_artifact(event, err_artifact))
        
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.critical("ExecutionBus: Byzantine fault in skill_id=%s", event.skill_id, exc_info=True)
        err_artifact = {
            "command": event.payload.get("command", "unknown"),
            "status": "error",
            "report": None,
            "issues": [{"severity": "fatal", "message": f"Unhandled exception: {exc}"}],
            "detail": {"error_type": type(exc).__name__, "traceback": traceback.format_exc(), "execution_time_ms": round(elapsed_ms, 2)},
            "trace_id": event.trace_id,
        }
        return ExecutionResult(artifact=_sign_artifact(event, err_artifact))
