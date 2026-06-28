# [C5-REAL] Exergy-Maximized
"""
CORTEX - Mac Maestro Autonomous Agent.

Executes natural language UI automation requests by dynamically generating
and executing AppleScript via the LLM.
"""

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from cortex.extensions.llm.router import CortexPrompt, IntentProfile
from cortex.extensions.ui_control.maestro import MaestroUI

if TYPE_CHECKING:
    from cortex.engine.core.cortex_engine import CortexEngine

logger = logging.getLogger("cortex_extensions.agents.mac_maestro")

SYSTEM_PROMPT = """
You are Mac Maestro, a sovereign macOS automation agent.
Your goal is to translate user natural language requests into valid AppleScript.
You must return a JSON block with the following structure:
{
    "explanation": "Brief reasoning of what this script will do",
    "script": "The pure AppleScript code to execute"
}
Do not include any other markdown or text outside the JSON block.
Ensure the AppleScript is robust, uses System Events where needed, and avoids syntax errors.
"""


class MacMaestroAgent:
    """Agent that translates natural language to AppleScript and executes it."""

    def __init__(self, engine: "CortexEngine | None" = None) -> None:
        self.engine = engine
        self.maestro = MaestroUI(engine)
        if engine and hasattr(engine, "llm_router"):
            self.router = engine.llm_router
        else:
            try:
                from cortex.pipeline.provider_factory import build_executor_stack

                _, router = build_executor_stack()
                self.router = router
            except Exception as e:
                logger.warning("Could not initialize CortexLLMRouter: %s", e)

    async def execute(self, instruction: str) -> dict[str, Any]:
        """
        Translates instruction, runs the script, and returns the result.
        """
        if not self.router:
            return {
                "success": False,
                "error": "No LLM router configured. Mac Maestro requires an active LLM.",
            }

        logger.info("Mac Maestro processing instruction: %s", instruction)

        prompt = CortexPrompt(  # type: ignore[call-arg]
            system=SYSTEM_PROMPT,  # type: ignore[call-arg]
            prompt=instruction,  # type: ignore[call-arg]
            intent=IntentProfile.CODE,
            temperature=0.1,
        )

        response_result = await self.router.execute_resilient(prompt)

        if not response_result or not response_result.is_ok():
            return {
                "success": False,
                "error": f"LLM returned error or empty response: {getattr(response_result, 'error', 'Unknown error')}",
            }

        response = response_result.unwrap()

        # Parse JSON
        script_data = self._parse_json_response(response)
        if not script_data or "script" not in script_data:
            return {"success": False, "error": f"Failed to parse JSON. Raw output: {response}"}

        script_code = script_data["script"]
        explanation = script_data.get("explanation", "Extracted AppleScript.")
        logger.info("Generated AppleScript: %s", explanation)

        # Execute via sovereign MaestroUI stack
        try:
            stdout = await self.maestro.run_applescript(script_code, require_success=True)
            success = True
            stderr = ""
        except (ValueError, TypeError, OSError, KeyError) as e:
            success = False
            stdout = ""
            stderr = str(e)

        return {
            "success": success,
            "explanation": explanation,
            "stdout": stdout,
            "stderr": stderr,
            "script": script_code,
        }

    def _parse_json_response(self, text: str) -> dict[str, Any] | None:
        try:
            return json.loads(text)
        except Exception as exc:
            logger.warning("Suppressed exception: %s", exc)

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)

        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)

        return None
