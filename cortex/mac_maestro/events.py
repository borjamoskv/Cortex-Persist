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
    role: str | None,
    title: str | None,
    identifier: str | None,
    ok: bool,
    latency_ms: int,
    error: str | None = None,
    verified: bool | None = None,
    verification_error: str | None = None,
    intent: IntentPayload | None = None,
    correlation_id: str | None = None,
    trace_id: str | None = None,
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
