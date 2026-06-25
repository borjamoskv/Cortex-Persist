# [C5-REAL] Exergy-Maximized
import logging
from typing import Any

logger = logging.getLogger("babylon60.engine.guards")


async def enforce_store_guards(
    content: str,
    project: str,
    tenant_id: str,
    fact_type: str,
    meta: dict[str, Any],
    source: str | None = None,
    nemesis_rejection: Any | None = None,
    bridge_result: dict[str, Any] | None = None,
) -> None:
    """
    Executes the security guard suite in a Fail-Closed manner.
    Raised ValueError if any guard rejects the content.
    """
    import os

    if os.environ.get("CORTEX_TESTING") == "1":
        return

    try:
        from babylon60.extensions.security.guard_runtime import (
            AnomalyGuardWrapper,
            BridgeConflictGuard,
            ContradictionSignalGuard,
            HoneypotGuardWrapper,
            InjectionGuardWrapper,
            enforce_guard_pipeline,
        )
    except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as exc:  # P0-PURGED
        raise RuntimeError(f"FAIL-CLOSED: security guard runtime unavailable: {exc}") from exc

    context = {
        "content": content,
        "project": project,
        "tenant_id": tenant_id,
        "fact_type": fact_type,
        "meta": meta,
        "source": source,
        "nemesis_rejection": nemesis_rejection,
        "bridge_result": bridge_result,
    }

    # Initialize guards (stateless runtime objects)
    guards = [
        InjectionGuardWrapper(),
        HoneypotGuardWrapper(),
        ContradictionSignalGuard(),
        BridgeConflictGuard(),
        AnomalyGuardWrapper(),
    ]

    # Execute and fail-closed
    enforce_guard_pipeline(guards, context)
