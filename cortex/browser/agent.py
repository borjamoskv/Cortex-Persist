import asyncio
import json
import logging
from typing import Any

from cortex.browser.engine import BrowserEngine
from cortex.llm.provider import LLMProvider
from cortex.llm.router import IntentProfile

LOG = logging.getLogger("cortex.browser")


class SovereignBrowserAgent:
    """
    Cognitive Loop for BROWSER-Ω.
    Observes the simplified DOM, reasons, and executes actions to achieve an objective.
    """

    def __init__(
        self, objective: str, llm_provider: LLMProvider | None = None, headless: bool = False
    ):
        self.objective = objective
        self.engine = BrowserEngine(headless=headless)  # Controlled by initialization
        self.llm = llm_provider or LLMProvider()
        self.max_steps = 15

    async def run(self, start_url: str):
        """Runs the autonomous browsing loop."""
        LOG.info("BROWSER-Ω: Objective initialized -> %s", self.objective)
        await self.engine.start()

        try:
            await self.engine.goto(start_url)
        except RuntimeError as e:
            LOG.error("BROWSER-Ω: Failed to reach start URL: %s", e)
            await self.engine.stop()
            raise

        try:
            for step in range(self.max_steps):
                LOG.info("BROWSER-Ω: Step %d/%d", step + 1, self.max_steps)

                # 1. Observe
                parse_result = await self.engine.parse_dom()
                dom_tree = parse_result.get("dom", "")
                if not dom_tree:
                    LOG.warning("BROWSER-Ω: No interactive elements found.")

                # 2. Reason
                action = await self._decide_next_action(dom_tree)
                LOG.info("BROWSER-Ω: Decided action -> %s", action)

                # 3. Act
                cmd = action.get("cmd")
                if cmd == "done":
                    LOG.info("BROWSER-Ω: Objective complete. Result: %s", action.get("result"))
                    break
                elif cmd == "click":
                    cortex_id = action.get("cortex_id")
                    await self.engine.click(int(cortex_id))  # type: ignore[reportArgumentType]
                elif cmd == "type":
                    cortex_id = action.get("cortex_id")
                    text = action.get("text")
                    await self.engine.type(int(cortex_id), text)  # type: ignore[reportArgumentType]
                elif cmd == "goto":
                    url = action.get("url")
                    await self.engine.goto(url)  # type: ignore[reportArgumentType]
                elif cmd == "wait":
                    wait_time_sec = action.get("seconds", 2)
                    await asyncio.sleep(wait_time_sec)
                elif cmd == "abort":
                    LOG.error(
                        "BROWSER-Ω: Agent requested abort or critical failure threshold reached."
                    )
                    break
                else:
                    LOG.error("BROWSER-Ω: Unknown command %s", cmd)

                await asyncio.sleep(1)  # Small pause for stability

        finally:
            await self.engine.stop()

    async def _decide_next_action(self, dom_tree: str) -> dict[str, Any]:
        """Provides the LLM with the context and gets the next action."""

        system_prompt = """
You are BROWSER-Ω, a sovereign web-automation agent.
Your objective is given by the user.
You will be provided with a simplified, semantic DOM tree of interactive elements.
Each element has a numeric ID like [12].

You must respond ONLY with a JSON object representing your next action. No formatting.

Actions:
1. Click an element: {"cmd": "click", "cortex_id": 12}
2. Type into an element: {"cmd": "type", "id": 15, "text": "query"}
3. Navigate to a URL: {"cmd": "goto", "url": "https://example.com"}
4. Wait for page to load: {"cmd": "wait", "seconds": 2}
5. Objective achieved: {"cmd": "done", "result": "Extracted information here"}

Ensure the JSON is perfectly valid.
"""
        user_prompt = f"""
OBJECTIVE: {self.objective}

CURRENT INTERACTIVE DOM:
{dom_tree}

What is your next action?
"""
        try:
            # We use the CORTEX LLMProvider's complete method
            response_text = await self.llm.complete(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.1,
                max_tokens=500,
                intent=IntentProfile.REASONING,
            )

            # The LLM should return a JSON string, let's parse it
            # Strip any markdown blocks if present
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:-3].strip()
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:-3].strip()

            return json.loads(clean_text)
        except json.JSONDecodeError as decode_err:
            LOG.error("BROWSER-Ω: Failed to parse LLM JSON response: %s", decode_err)
            raise ValueError(
                f"BROWSER-Ω: Invalid JSON structure from LLM -> {decode_err}"
            ) from decode_err
        # General exceptions intentionally bubble up to elevate API/network failures
        # to the CORTEX orchestrator immediately instead of masking them.
