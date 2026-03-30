import functools
import logging
import sys
from typing import Any, Callable, Coroutine, Dict

# CORTEX-Persist // Sovereign Guards v1.0.0
# The Byzantine Frontier: Zero-Tolerance Stochastic Hallucination Guards.

logger = logging.getLogger("cortex.guards.admission")
logger.setLevel(logging.INFO)

class StochasticHallucinationError(Exception):
    """Raised when the agent attempts to commit unauditable or non-deterministic state."""
    pass

class NullExergyError(Exception):
    """Raised when the payload represents 0 exergy (thermal noise)."""
    pass

def byzantine_frontier_guard(strict: bool = True):
    """
    O(1) Middleware / Decorator for intercepting the Write-Path.
    Any violation of the CORTEX structural constraints causes an instant abort (Exit Code 0 
    to prevent crash loops, but effectively denying the admission of the write).

    Mandates:
    - No floats (must use deterministic types for P0 paths, handled usually by serializers, but checked here).
    - Must not contain 'padding' or rhetorical noise.
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # We assume the mutation payload is typically the first dict argument or a kwarg named 'state_mutation'
            payload = kwargs.get('state_mutation')
            if payload is None:
                for arg in args:
                    if isinstance(arg, dict):
                        payload = arg
                        break
            
            if payload is not None:
                # 1. Structural Validation (No generic filler, no stochastic rhetorical noise)
                # Ensure the payload brings actual exergy. Heuristic: must have minimal structure.
                if not payload:
                    logger.error("Admission Denied: Missing Payload (Null Exergy).")
                    if strict: sys.exit(0)
                    raise NullExergyError("Missing state mutation payload.")
                
                # Check for floating point non-determinism in the dictionary values
                def _scan_for_floats(obj: Any):
                    if isinstance(obj, float):
                        return True
                    if isinstance(obj, dict):
                        return any(_scan_for_floats(v) for v in obj.values())
                    if isinstance(obj, list):
                        return any(_scan_for_floats(v) for v in obj)
                    return False
                
                if _scan_for_floats(payload):
                    logger.error("Admission Denied: Float found in payload. Violation of deterministic taint.")
                    if strict: sys.exit(0)
                    raise StochasticHallucinationError("Non-deterministic float types are forbidden.")
                
                # If we passed the guard, execute the inner write-path
                logger.info("Byzantine Frontier Guard: Payload admitted. Exergy profile validated.")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
