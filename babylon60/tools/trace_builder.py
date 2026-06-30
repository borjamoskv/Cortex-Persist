"""TraceBuilder: constructs ExecutionTrace from runtime audit events.

Usage (shadow mode — does not touch hot-path):

    builder = TraceBuilder(tenant_id="t1", model_version="0.9", op_kind="write")
    builder.record("write", fact_id="f42", ledger_height=1001, payload_hash="abc")
    builder.record("commit", ledger_height=1002)
    trace = builder.build()

The resulting ExecutionTrace satisfies the Trajectory Protocol used by
MetaArbiterKernel and energy_fn components.
"""

from __future__ import annotations

import time
import uuid

from babylon60.tools.trace_adapter import ExecutionTrace, TraceEvent


class TraceBuilder:
    """Collects audit events and emits a sealed ExecutionTrace.

    Designed for shadow / offline use: call record() at each
    observable point in the engine, then build() to seal.
    """

    # Event kinds that produce ledger-visible artifacts.
    _PERSISTED_KINDS: frozenset[str] = frozenset({"write", "commit", "fact"})

    def __init__(
        self,
        tenant_id: str | None,
        model_version: str,
        op_kind: str,
        trace_id: str | None = None,
    ) -> None:
        self._id = trace_id or str(uuid.uuid4())
        self._tenant_id = tenant_id
        self._model_version = model_version
        self._op_kind = op_kind
        self._events: list[TraceEvent] = []
        self._start = time.monotonic()

    @property
    def trace_id(self) -> str:
        return self._id

    def record(
        self,
        kind: str,
        *,
        fact_id: str | None = None,
        ledger_height: int | None = None,
        payload_hash: str | None = None,
    ) -> None:
        """Append a single event to the trace.

        Parameters
        ----------
        kind:          Event type string.
        fact_id:       Optional fact identifier involved in this event.
        ledger_height: Ledger height at the time of the event, if known.
        payload_hash:  Hash of the payload, for replay/projection verification.
        """
        self._events.append(
            TraceEvent(
                kind=kind,
                fact_id=fact_id,
                tenant_id=self._tenant_id,
                timestamp=time.monotonic(),
                ledger_height=ledger_height,
                payload_hash=payload_hash,
                is_write=(kind == "write"),
                is_read=(kind == "read"),
                is_mutation=(kind == "mutation"),
                is_persisted_event=(kind in self._PERSISTED_KINDS),
            )
        )

    def build(self) -> ExecutionTrace:
        """Seal and return the ExecutionTrace. Builder becomes read-only after this."""
        return ExecutionTrace(
            id=self._id,
            tenant_id=self._tenant_id,
            model_version=self._model_version,
            op_kind=self._op_kind,
            start_time=self._start,
            end_time=time.monotonic(),
            _events=list(self._events),
        )

    def __len__(self) -> int:
        return len(self._events)
