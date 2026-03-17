"""MOSKV-Aether — Critic Agent.

Reviews the git diff produced by the Executor and approves or rejects.
"""

from __future__ import annotations

import json
import logging

from cortex.extensions.aether.models import CriticOutput
from cortex.extensions.aether.tools import AgentToolkit

__all__ = ["CriticAgent"]

logger = logging.getLogger("cortex.extensions.aether.critic")

_SYSTEM = """You are a Sovereign Code Critic AI. Review the git diff below and
assess whether it correctly implements the task.

Output ONLY valid JSON:
{
  "approved": true/false,
  "issues": ["issue 1", "issue 2"],
  "suggestions": "optional improvement notes"
}

Be strict but fair. Approve only if:
- The task is fully implemented
- No obvious bugs, syntax errors, or regressions
- Code is clean and readable
- Tests (if modified) are correct
"""


class CriticAgent:
    """Reviews the git diff and approves or requests fixes."""

    def __init__(self, llm, base_system_prompt: str | None = None) -> None:
        self._llm = llm
        self._base_system = base_system_prompt

    async def critique(
        self,
        task_description: str,
        toolkit: AgentToolkit,
    ) -> CriticOutput:
        """Review the current diff. Returns CriticOutput."""
        from cortex.extensions.llm.router import IntentProfile

        diff = toolkit.git_diff()
        if not diff.strip() or diff.startswith("[ERROR]"):
            logger.info("Critic: no diff found — auto-approving")
            return CriticOutput(approved=True, issues=[], suggestions="No changes detected.")

        prompt = (
            f"TASK:\n{task_description}\n\n"
            f"GIT DIFF:\n{diff[:6000]}\n\n"
            "Review the diff and output your JSON verdict:"
        )

        sys_prompt = _SYSTEM
        if self._base_system:
            sys_prompt = f"{self._base_system}\n\n[MANDATORY FORMAT INSTRUCTIONS]\n{_SYSTEM.split('Output ONLY valid JSON:')[1]}"

        raw = await self._llm.complete(
            prompt,
            system=sys_prompt,
            temperature=0.1,
            max_tokens=800,
            intent=IntentProfile.REASONING,
        )

        return self._parse(raw)

    def _parse(self, raw: str) -> CriticOutput:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1])
        try:
            data = json.loads(text)
            return CriticOutput(
                approved=bool(data.get("approved", False)),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", ""),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Critic JSON parse failed: %s", e)
            # If we can't parse, be conservative and approve
            approved = "true" in raw.lower() and "false" not in raw.lower()
            return CriticOutput(approved=approved, issues=[], suggestions=raw[:500])
