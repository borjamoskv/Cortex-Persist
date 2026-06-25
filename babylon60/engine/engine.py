# [C5-REAL] Cortex Execution Engine
import logging
import time
from typing import Any

from babylon60.engine import execution_ledger as ledger
from babylon60.engine.cost_scheduler import ExergyCostScheduler

logger = logging.getLogger("babylon60.engine.engine")

cost_scheduler = ExergyCostScheduler()


class HitlStore:
    def enqueue(self, intent: dict, driver: Any = None) -> str:
        logger.info(f"[HITL] Enqueued intent: {intent}")
        return "hitl_row_pending_001"


hitl_store = HitlStore()
cdp_driver = None


async def cdp_execute(intent: dict) -> dict:
    """Execute intent via CDP (C4-SIM fallback)."""
    logger.info(f"[CDP] Executing intent: {intent}")
    return {"status": "success", "backend": "CDP", "intent": intent}


def ax_execute(intent: dict) -> dict:
    """Execute intent via AX (C4-SIM fallback)."""
    logger.info(f"[AX] Executing intent: {intent}")
    return {"status": "success", "backend": "AX", "intent": intent}


async def run(intent: dict, domain: str = "") -> dict:
    """Execute decision and record performance/cost in the execution ledger."""
    backend = cost_scheduler.select_backend(domain, intent["kind"])
    t0 = time.perf_counter()
    outcome, error_type = "success", None

    try:
        if backend.name == "CDP":
            result = await cdp_execute(intent)
        elif backend.name == "AX":
            result = ax_execute(intent)
        elif backend.name == "HITL":
            row_id = hitl_store.enqueue(intent, driver=cdp_driver)
            result = {"status": "hitl_pending", "row_id": row_id}
        else:
            raise ValueError(f"Unknown backend type: {backend.name}")
    except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
        outcome = "failure"
        error_type = type(e).__name__
        raise
    finally:
        ledger.record(
            intent_kind=intent["kind"],
            domain=domain,
            backend=backend.name,
            cost_eval=backend.total_cost(domain),
            outcome=outcome,
            duration_ms=int((time.perf_counter() - t0) * 1000),
            error_type=error_type,
        )

    return result
