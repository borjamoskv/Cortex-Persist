"""MOSKV-Aether — Executor Agent.

Iterative tool-calling loop. Parses <tool_call> XML from LLM output
and dispatches to AgentToolkit. No framework dependency.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from cortex.aether.models import PlanOutput, ToolCall
from cortex.aether.tools import AgentToolkit

__all__ = ["ExecutorAgent"]

logger = logging.getLogger("cortex.aether.executor")

_MAX_ITERATIONS = 30

_SYSTEM = """You are AETHER: The Cognitive Medium of the CORTEX OS.
You implement code changes step by step using tools. You are the quintessence of the codebase,
the medium through which intent manifests as implementation.

AVAILABLE TOOLS:
- read_file(path)           — read a file
- write_file(path, content) — write/overwrite a file
- list_dir(path)            — list directory
- bash(cmd)                 — run a shell command
- git_diff()                — show current diff
- git_status()              — show git status
- git_commit(message)       — commit all staged changes
- web_search(query)         — search the web for docs/examples
- autodidact_ingest(target_url, intent) — USE THIS as a semantic scalpel to ingest
  knowledge gaps (docs/APIs). Intent should be specific (e.g. 'extract migration patterns').

TOOL CALL FORMAT (use this exact XML):
<tool_call>
  <name>tool_name</name>
  <args>
    <key>value</key>
  </args>
</tool_call>

When all changes are complete and committed, output exactly: <done/>

Rules:
- Do ONE tool call per response
- Read files before modifying them
- Always commit when done
- If a test fails, fix the code and retry
- Never escape the repo directory
"""


@dataclass
class ExecutorState:
    """Mutable state across Executor iterations."""

    messages: list[dict] = field(default_factory=list)
    iterations: int = 0
    done: bool = False
    last_tool: str = ""
    tool_results: list[str] = field(default_factory=list)


class ExecutorAgent:
    """Iterative tool-calling executor agent."""

    def __init__(self, llm) -> None:
        self._llm = llm

    async def execute(
        self,
        plan: PlanOutput,
        task_description: str,
        toolkit: AgentToolkit,
    ) -> str:
        """Run the execution loop. Returns a summary of what was done."""
        from cortex.llm.router import IntentProfile

        state = ExecutorState()
        state.messages = [
            {
                "role": "system",
                "content": _SYSTEM,
            },
            {
                "role": "user",
                "content": (
                    f"TASK:\n{task_description}\n\n"
                    f"{plan.to_prompt_str()}\n\n"
                    "Start executing the plan now. Use tools one at a time."
                ),
            },
        ]

        while state.iterations < _MAX_ITERATIONS and not state.done:
            state.iterations += 1
            logger.info("⚙️  Executor iteration %d/%d", state.iterations, _MAX_ITERATIONS)

            # Build prompt from message history
            prompt = self._build_prompt(state.messages)

            response = await self._llm.complete(
                prompt,
                system=_SYSTEM,
                temperature=0.1,
                max_tokens=2000,
                intent=IntentProfile.CODE,
            )

            state.messages.append({"role": "assistant", "content": response})

            if "<done/>" in response or "<done />" in response:
                state.done = True
                logger.info("✅ Executor signalled <done/> at iteration %d", state.iterations)
                break

            # Parse and dispatch tool call
            tool_call = self._parse_tool_call(response)
            if tool_call:
                state.last_tool = tool_call.name
                result = toolkit.dispatch(tool_call.name, tool_call.args)
                state.tool_results.append(f"[{tool_call.name}] → {result[:500]}")
                logger.debug("Tool [%s] result: %s", tool_call.name, result[:200])
                state.messages.append({
                    "role": "user",
                    "content": f"Tool result:\n{result}\n\nContinue with the next step.",
                })
            else:
                # No tool call found — prompt agent to use a tool or finish
                state.messages.append({
                    "role": "user",
                    "content": (
                        "No tool call detected. Either call a tool using <tool_call>...</tool_call>"
                        " or signal completion with <done/> if all work is done."
                    ),
                })

        if not state.done:
            logger.warning("Executor hit max iterations (%d)", _MAX_ITERATIONS)

        summary = f"Completed in {state.iterations} iterations.\n"
        summary += "\n".join(state.tool_results[-10:])
        return summary

    def _build_prompt(self, messages: list[dict]) -> str:
        """Flatten message history into a single prompt string."""
        parts = []
        for msg in messages[1:]:  # skip system (passed separately)
            role = msg["role"].upper()
            parts.append(f"[{role}]\n{msg['content']}")
        return "\n\n".join(parts)

    @staticmethod
    def _parse_tool_call(text: str) -> ToolCall | None:
        """Extract first <tool_call> block from LLM output."""
        match = re.search(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL)
        if not match:
            return None
        xml_str = f"<tool_call>{match.group(1)}</tool_call>"
        try:
            root = ET.fromstring(xml_str)
            name_el = root.find("name")
            if name_el is None or not name_el.text:
                return None
            name = name_el.text.strip()
            args_el = root.find("args")
            args: dict[str, str] = {}
            if args_el is not None:
                for child in args_el:
                    args[child.tag] = (child.text or "").strip()
            return ToolCall(name=name, args=args)
        except ET.ParseError as e:
            logger.debug("Tool call XML parse error: %s", e)
            return None
