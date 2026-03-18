"""
MacMaestroBridge — Sovereign bridge between CORTEX and MacMaestro-Ω SDK.

Translates high-level automation intents into executed UIAction sequences
following the Master Protocol.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sdks.mac_maestro.models import ActionFailed, UIAction
from sdks.mac_maestro.workflow import MacMaestroWorkflow

logger = logging.getLogger("cortex.extensions.automation.bridge")


class MaestroActionRunner:
    """Encapsulates MacMaestro-Ω workflow execution for CORTEX."""

    def __init__(self, bundle_id: str):
        self.bundle_id = bundle_id
        self.workflow = MacMaestroWorkflow(bundle_id=bundle_id)

    async def run_intent(
        self,
        intent_data: dict[str, Any],
        apply_safety_gate: bool = True,
    ) -> dict[str, Any]:
        """
        Executes an automation intent.

        Intent Data Schema:
        {
            "action": "click" | "type" | "hotkey" | "sequence",
            "target": {"role": "button", "title": "Save", ...},
            "payload": "text to type" | ["key", "mod"],
            "unsafe_override": bool
        }
        """
        action_name = intent_data.get("action", "inspect")
        target_query = intent_data.get("target", {})
        unsafe = intent_data.get("unsafe_override", False)

        # Determine vector based on action
        if action_name in ["click", "inspect"]:
            vector = "B"
        elif action_name == "type":
            vector = "C"
        else:
            vector = "A"  # Default to AppleScript for unknown actions

        # Build UIAction
        action = UIAction(
            name=action_name,
            vector=vector,
            target_query=target_query,
            unsafe=unsafe,
        )

        try:
            logger.info("Executing Maestro intent: %s on %s", action_name, self.bundle_id)
            # Properly run sync SDK in thread pool to avoid blocking event loop
            success = await asyncio.to_thread(
                self.workflow.execute_action, action, apply_safety_gate,
            )

            return {
                "success": success,
                "bundle_id": self.bundle_id,
                "action": action_name,
                "trace_id": self.workflow.run_id,
            }
        except ActionFailed as e:
            logger.error("Maestro action failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "bundle_id": self.bundle_id,
                "trace_id": self.workflow.run_id,
            }
        except PermissionError as e:
            logger.warning("Safety gate blocked action: %s", e)
            return {
                "success": False,
                "error": "SAFETY_GATE_BLOCKED",
                "message": str(e),
                "bundle_id": self.bundle_id,
            }


async def execute_maestro_flow(bundle_id: str, intent_data: dict[str, Any]) -> dict[str, Any]:
    """Helper for one-shot automation execution."""
    runner = MaestroActionRunner(bundle_id)
    return await runner.run_intent(intent_data)
