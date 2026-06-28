# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request

from cortex.ledger.models import IntentPayload
from cortex.ledger.writer import LedgerWriter
from cortex.mac_maestro.events import build_mac_maestro_event
from cortex.mac_maestro.intent import MacAction, MacIntent
from cortex.mac_maestro.oracle import VerificationOracle

logger = logging.getLogger("cortex.mac_maestro.executor")


class MaestroExecutor:
    """Executes MacIntents via Mac-Control-OMEGA Daemon and logs to the sovereign ledger."""

    def __init__(self, ledger_writer: LedgerWriter) -> None:
        self.ledger_writer = ledger_writer
        self.omega_url = os.environ.get("OMEGA_BIND_HOST", "127.0.0.1")
        self.omega_port = int(os.environ.get("OMEGA_BIND_PORT", "8011"))
        self.api_url = f"http://{self.omega_url}:{self.omega_port}/api/v1/dispatch"

        self.omega_token = os.environ.get("OMEGA_DAEMON_TOKEN", "")
        if not self.omega_token:
            token_file = "/tmp/omega_daemon.token"
            if os.path.exists(token_file):
                with open(token_file) as f:
                    self.omega_token = f.read().strip()

    def _convert_action(self, action: MacAction) -> dict:
        """Translates a Cortex MacAction into an OMEGA Daemon CommandReq."""

        # If it's a direct domain mapping
        if action.action.startswith("mac_"):
            parts = action.action.split("_")
            if len(parts) >= 3:
                # e.g., mac_display_set_brightness -> domain=display, action=set_brightness
                domain = parts[1]
                omega_action = "_".join(parts[2:])
                return {
                    "domain": domain,
                    "action": omega_action,
                    "args": action.payload
                    if isinstance(action.payload, list)
                    else ([action.payload] if action.payload else []),
                }

        # Legacy UI mapping heuristic
        return {
            "domain": "automation",
            "action": action.action,
            "args": [action.app, action.title, action.identifier, action.payload],
        }

    def execute_intent(
        self,
        intent: MacIntent,
        oracle: VerificationOracle | None = None,
        apply_safety_gate: bool = True,
    ) -> list[str]:
        """
        Executes a sequence of actions via Mac-Control-OMEGA, verifying them and logging to the ledger.
        Returns a list of ledger event IDs.
        """
        if not self.omega_token:
            logger.warning("No OMEGA_DAEMON_TOKEN found. Mac-Control-OMEGA daemon might reject.")

        event_ids = []
        cortex_intent = IntentPayload(
            goal=intent.goal,
            task_id=intent.correlation_id,
        )

        for action in intent.actions:
            start_time = time.perf_counter()
            req_data = self._convert_action(action)

            ok = False
            error_msg = None
            verification_ok = None
            verification_error = None
            trace_id = "OMEGA"

            try:
                logger.info(
                    "Executing Mac action via OMEGA: %s.%s", req_data["domain"], req_data["action"]
                )
                req = urllib.request.Request(
                    self.api_url,
                    data=json.dumps(req_data).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.omega_token}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30.0) as resp:
                    resp_body = json.loads(resp.read().decode("utf-8"))
                    if resp_body.get("status") == "success":
                        ok = True
                    else:
                        error_msg = resp_body.get("error", "Unknown Daemon Error")
            except urllib.error.HTTPError as e:
                error_msg = f"HTTP_ERROR: {e.code} - {e.reason}"
            except (ValueError, TypeError, OSError, KeyError) as e:
                error_msg = f"SYS_ERROR: {e}"

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if ok and oracle:
                verdict = oracle.verify()
                verification_ok = verdict.verified
                verification_error = verdict.reason

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
                trace_id=intent.trace_id or trace_id,
            )

            event_id = self.ledger_writer.append(event)
            event_ids.append(event_id)

            if not ok or verification_ok is False:
                logger.warning("Intent sequence broken at action: %s", action.action)
                break

        return event_ids
