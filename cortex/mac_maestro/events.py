from typing import Optional

from cortex.ledger.models import (
    ActionResult,
    ActionTarget,
    IntentPayload,
    LedgerEvent,
)


def build_mac_maestro_event(
    *,
    action: str,
    app: str,
    role: Optional[str],
    title: Optional[str],
    identifier: Optional[str],
    ok: bool,
    latency_ms: int,
    error: Optional[str] = None,
    verified: Optional[bool] = None,
    verification_error: Optional[str] = None,
    intent: Optional[IntentPayload] = None,
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> LedgerEvent:
    return LedgerEvent.new(
        tool="mac_maestro",
        actor="agent",
        action=action,
        target=ActionTarget(
            app=app,
            role=role,
            title=title,
            identifier=identifier,
        ),
        result=ActionResult(
            ok=ok,
            latency_ms=latency_ms,
            error=error,
            verified=verified,
            verification_error=verification_error,
        ),
        intent=intent,
        correlation_id=correlation_id,
        trace_id=trace_id,
    )
