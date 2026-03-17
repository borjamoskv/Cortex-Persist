"""
CORTEX - Mac Maestro Autonomous Agent.

Executes natural language UI automation requests by dynamically generating
and executing AppleScript via the LLM.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from cortex.extensions.llm.manager import LLMManager
from cortex.extensions.llm.router import IntentProfile
from cortex.utils.applescript import run_applescript

logger = logging.getLogger("cortex.extensions.agents.mac_maestro")

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

    def __init__(self) -> None:
        self.llm = LLMManager()

    async def execute(self, instruction: str) -> dict[str, Any]:
        """
        Translates instruction, runs the script, and returns the result.
        """
        if not self.llm.available:
            return {
                "success": False,
                "error": "No LLM provider configured. Mac Maestro requires an active LLM.",
            }

        logger.info("Mac Maestro processing instruction: %s", instruction)

        response = await self.llm.complete(
            prompt=instruction,
            system=SYSTEM_PROMPT,
            temperature=0.1,
            intent=IntentProfile.CODE,
        )

        if not response:
            return {"success": False, "error": "LLM returned empty response."}

        # Parse JSON
        script_data = self._parse_json_response(response)
        if not script_data or "script" not in script_data:
            return {"success": False, "error": f"Failed to parse JSON. Raw output: {response}"}

        script_code = script_data["script"]
        explanation = script_data.get("explanation", "Extracted AppleScript.")
        logger.info("Generated AppleScript: %s", explanation)

        # Execute
        success, stdout, stderr = await run_applescript(script_code)

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
        except json.JSONDecodeError:
            pass

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return None
