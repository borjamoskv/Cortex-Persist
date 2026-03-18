from __future__ import annotations

import logging
import time
from typing import Optional

from cortex.ledger.models import IntentPayload
from cortex.ledger.writer import LedgerWriter
from cortex.mac_maestro.events import build_mac_maestro_event
from cortex.mac_maestro.intent import MacAction, MacIntent
from cortex.mac_maestro.oracle import VerificationOracle

try:
    from sdks.mac_maestro.models import ActionFailed, UIAction
    from sdks.mac_maestro.workflow import MacMaestroWorkflow

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


logger = logging.getLogger("cortex.mac_maestro.executor")


class MaestroExecutor:
    """Executes MacIntents via MacMaestro-Ω SDK and logs to the sovereign ledger."""

    def __init__(self, ledger_writer: LedgerWriter) -> None:
        self.ledger_writer = ledger_writer

    def _convert_action(self, action: MacAction) -> UIAction:
        """Translates a Cortex MacAction into an SDK UIAction."""
        if not SDK_AVAILABLE:
            raise RuntimeError("MacMaestro SDK is not installed or available.")

        target_query: dict[str, str] = {}
        if action.role:
            target_query["role"] = action.role
        if action.title:
            target_query["title"] = action.title
        if action.identifier:
            target_query["identifier"] = action.identifier

        # Simple vector routing logic
        if action.action in ("click", "inspect"):
            vector = "B"
        elif action.action == "type":
            vector = "C"
        else:
            vector = "A"

        return UIAction(
            name=action.action,
            vector=vector,
            target_query=target_query,
            unsafe=action.unsafe_override,
            # Payload isn't mapped directly in UIAction without custom extension,
            # assuming it gets handled by workflow logic if passed directly or injected into target_query
        )

    def execute_intent(
        self,
        intent: MacIntent,
        oracle: Optional[VerificationOracle] = None,
        apply_safety_gate: bool = True,
    ) -> list[str]:
        """
        Executes a sequence of actions, verifying them and logging to the ledger.
        Returns a list of ledger event IDs.
        """
        if not SDK_AVAILABLE:
            raise RuntimeError("Cannot execute MacIntent without MacMaestro SDK.")

        event_ids = []
        cortex_intent = IntentPayload(
            goal=intent.goal,
            task_id=intent.correlation_id,
        )

        for action in intent.actions:
            start_time = time.perf_counter()
            sdk_action = self._convert_action(action)
            workflow = MacMaestroWorkflow(bundle_id=action.app)

            ok = False
            error_msg = None
            verification_ok = None
            verification_error = None

            try:
                # SDK Call
                logger.info("Executing Mac action: %s on %s", action.action, action.app)
                ok = workflow.execute_action(sdk_action, apply_safety_gate=apply_safety_gate)
            except ActionFailed as e:
                error_msg = str(e)
            except PermissionError as e:
                error_msg = f"SAFETY_GATE_BLOCK: {e}"
            except Exception as e:
                error_msg = f"SYS_ERROR: {e}"

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Oracle validation (optional, per step or end of intent)
            if ok and oracle:
                verdict = oracle.verify()
                verification_ok = verdict.verified
                verification_error = verdict.reason

            # Transform to strict LedgerEvent
            event = build_mac_maestro_event(
                action=action.action,
                app=action.app,
                role=action.role,
                title=action.title,
                identifier=action.identifier,
                ok=ok,
                latency_ms=latency_ms,
                error=error_msg,
                verified=verification_ok,
                verification_error=verification_error,
                intent=cortex_intent,
                correlation_id=intent.correlation_id,
                trace_id=intent.trace_id or workflow.run_id,
            )

            # Persist and cryptographic chain
            event_id = self.ledger_writer.append(event)
            event_ids.append(event_id)

            # Fail fast if sequence breaks
            if not ok or verification_ok is False:
                logger.warning("Intent sequence broken at action: %s", action.action)
                break

        return event_ids
