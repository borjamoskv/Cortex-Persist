# [C5-REAL] Exergy-Maximized
import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def seal_decision(fact_type: str, client_id_kwarg: str = "client_id"):
    """
    Parasitic Overlay Decorator.
    Seals a fiscal decision automatically into the CORTEX immutable ledger
    without requiring the user to re-architect their application.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 1. Execute the agent's logic normally (Zero Friction)
            result = func(*args, **kwargs)

            # 2. Extract context silently
            # Attempt to extract client_id from kwargs or default to "unknown_client"
            client_id = kwargs.get(client_id_kwarg, "unknown_client")

            # Extract bound arguments for tracing (inputs to the decision)
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Format inputs as a simple provenance chain trace
            inputs_trace = [
                f"{k}={v}"
                for k, v in bound_args.arguments.items()
                # Exclude large or non-serializable objects naively for this demo
                if isinstance(v, str | int | float | bool)
            ]

            # 3. Forge the TaxFact payload (C5-REAL integration)
            try:
                from babylon60.cli.common import get_engine
                from babylon60.events.loop import sovereign_run
                from babylon60.extensions.fiscal.models import TaxFact, TaxFactPayload

                # Parse result generically (assuming the agent returned a dict or we cast it to string)
                # In a real integration, result would be typed or mapped to TaxFactPayload
                payload = TaxFactPayload(
                    action=func.__name__,
                    amount_eur=0.0,  # Placeholder, should be mapped from result
                    tax_category="auto_extracted",
                    rationale=str(result)[:200],  # First 200 chars as rationale
                )

                fact = TaxFact(
                    fact_type=fact_type,
                    agent_id="auto-sealed-agent",
                    client_id=client_id,
                    period="current",
                    confidence=1.0,
                    payload=payload,
                    provenance_chain=inputs_trace,
                )

                # Persist asynchronously in the engine without blocking the user
                engine = get_engine()

                async def _persist_fact():
                    # We inject this directly into the semantic or ledger core.
                    # For demonstration, we simply log the semantic payload.
                    await engine.add_fact(fact_type, fact.to_dict())  # type: ignore

                sovereign_run(_persist_fact())
                logger.info(f"[CORTEX] Sealed decision {fact_type} for client {client_id}")

            except Exception as e:  # noqa: BLE001
                # Zero Friction: Do not crash the user's workflow if audit fails
                logger.error(f"[CORTEX] Failed to seal decision: {e}")

            return result

        return wrapper

    return decorator
