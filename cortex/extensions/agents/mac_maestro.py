"""
CORTEX - Mac Maestro Autonomous Agent.

Executes natural language UI automation requests by dynamically generating
and executing AppleScript via the LLM. Includes retry, validation, and
structured output enforcement.
"""

import json
import logging
import re
from typing import Any

from cortex.extensions.llm.manager import LLMManager
from cortex.extensions.llm.router import IntentProfile
from cortex.utils.applescript import run_applescript

logger = logging.getLogger("cortex.extensions.agents.mac_maestro")

MAX_LLM_RETRIES = 2

SYSTEM_PROMPT = """\
You are Mac Maestro, a sovereign macOS automation agent.
Your goal is to translate user natural language requests into valid AppleScript.

RESPONSE FORMAT (strict JSON, no markdown wrapping):
{
    "explanation": "Brief reasoning of what this script will do",
    "script": "The pure AppleScript code to execute"
}

REQUIREMENTS:
- Use `tell application "System Events"` for UI interactions.
- Use `tell application "Finder"` for file operations.
- Use `do shell script` for terminal commands.
- Always wrap multi-step scripts in `try`/`on error` blocks.
- For key presses, use `key code` with numeric keycodes.
- Do NOT use `display dialog` unless the user explicitly asks for it.
- Return ONLY the JSON. No markdown fences, no commentary.

COMMON ERRORS TO AVOID:
- Missing `end tell` for `tell` blocks.
- Using `keystroke` without `using` clause for modifier keys.
- Forgetting `activate` before interacting with an app window.
"""


class MacMaestroAgent:
    """Agent that translates natural language to AppleScript and executes it."""

    def __init__(self) -> None:
        self.llm = LLMManager()

    async def execute(
        self,
        instruction: str,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Translates instruction, validates, runs the script, and returns the result."""
        if not self.llm.available:
            return {
                "success": False,
                "error": "No LLM provider configured. Mac Maestro requires an active LLM.",
            }

        logger.info("Mac Maestro processing instruction: %s", instruction)

        # LLM with retry
        script_data = await self._generate_with_retry(instruction)
        if not script_data or "script" not in script_data:
            return {
                "success": False,
                "error": "Failed to generate valid AppleScript JSON after retries.",
            }

        script_code = script_data["script"]
        explanation = script_data.get("explanation", "Extracted AppleScript.")
        logger.info("Generated AppleScript: %s", explanation)

        # Validate before execution
        validation_error = _validate_script(script_code)
        if validation_error:
            logger.warning("Script validation failed: %s", validation_error)
            return {
                "success": False,
                "error": f"Script validation failed: {validation_error}",
                "script": script_code,
            }

        # Execute
        success, stdout, stderr = await run_applescript(script_code, timeout=timeout)

        return {
            "success": success,
            "explanation": explanation,
            "stdout": stdout,
            "stderr": stderr,
            "script": script_code,
        }

    async def _generate_with_retry(
        self,
        instruction: str,
    ) -> dict[str, Any] | None:
        """Attempt LLM generation with retry on JSON parse failure."""
        for attempt in range(MAX_LLM_RETRIES):
            response = await self.llm.complete(
                prompt=instruction,
                system=SYSTEM_PROMPT,
                temperature=0.1,
                intent=IntentProfile.CODE,
            )

            if not response:
                logger.warning("LLM returned empty response (attempt %d)", attempt + 1)
                continue

            script_data = self._parse_json_response(response)
            if script_data and "script" in script_data:
                return script_data

            logger.warning(
                "JSON parse failed (attempt %d/%d). Raw: %s",
                attempt + 1,
                MAX_LLM_RETRIES,
                response[:200],
            )

            # On retry, add error context to the prompt
            instruction = (
                f"Your previous response was not valid JSON. "
                f"Please return ONLY a JSON object with 'explanation' and 'script' keys. "
                f"Original request: {instruction}"
            )

        return None

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


def _validate_script(script: str) -> str | None:
    """Basic AppleScript syntax validation.

    Returns error message if invalid, None if OK.
    """
    if not script or not script.strip():
        return "Empty script."

    # Check balanced tell/end tell blocks
    tell_count = len(re.findall(r"\btell\b", script, re.IGNORECASE))
    end_tell_count = len(re.findall(r"\bend tell\b", script, re.IGNORECASE))
    if tell_count != end_tell_count:
        return (
            f"Unbalanced tell blocks: {tell_count} `tell` vs "
            f"{end_tell_count} `end tell`."
        )

    # Check for obviously dangerous commands
    dangerous = ["do shell script \"rm -rf", "do shell script \"sudo"]
    for pattern in dangerous:
        if pattern.lower() in script.lower():
            return f"Potentially dangerous command detected: {pattern}"

    return None

