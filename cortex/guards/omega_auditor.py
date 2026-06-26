# [C5-REAL] Exergy-Maximized
"""
CORTEX - Omega Auditor (Axiom 20 + Massive Context).

Deep semantic contradiction detection using Gemini 3 Pro (1M context).
This guard audits new decisions against the ENTIRE system snapshot.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

try:
    from cortex_extensions.llm.provider import LLMProvider
    from cortex_extensions.llm.router import CortexPrompt, IntentProfile
except ImportError:
    LLMProvider = None  # type: ignore
    CortexPrompt = None  # type: ignore
    IntentProfile = None  # type: ignore

logger = logging.getLogger("cortex.guards.omega")

SNAPSHOT_PATH = Path.home() / ".cortex" / "context-snapshot.md"


@dataclass(frozen=True)
class OmegaConflict:
    fact_id: str | None
    summary: str
    reasoning: str
    severity: str  # 'low' | 'medium' | 'high'


class OmegaAuditor:
    """Sovereign Auditor for deep semantic health."""

    def __init__(self, provider: str = "ollama"):
        if LLMProvider is not None:
            self._llm = LLMProvider(provider=provider)
            # Dynamic fallback selector enforced to Local Autarchy (Ollama / MLX)
            self._fallbacks = []
            self._fallbacks.append(
                LLMProvider(
                    provider="custom",
                    model="qwen2.5:32b",
                    base_url="http://127.0.0.1:11434/v1",
                    api_key="local-autarchy-key",
                )
            )
        else:
            self._llm = None
            self._fallbacks = []

    async def audit_decision(self, content: str, project: str) -> list[OmegaConflict]:
        """Audit a candidate decision against the massive context of the snapshot."""
        import os

        if (
            os.environ.get("CORTEX_TESTING") == "1"
            and os.environ.get("CORTEX_STRICT_GUARDS") != "1"
            and os.environ.get("CORTEX_FORCE_OMEGA") != "1"
        ):
            logger.warning("OmegaAuditor: CORTEX_TESTING is enabled. Skipping deep audit.")
            return []

        if self._llm is None or CortexPrompt is None or IntentProfile is None:
            logger.warning("OmegaAuditor: LLM extension missing. Skipping deep audit.")
            return []

        if not SNAPSHOT_PATH.exists():
            logger.warning(
                "OmegaAuditor: Snapshot missing at %s. Skipping deep audit.", SNAPSHOT_PATH
            )
            return []

        try:
            snapshot_text = SNAPSHOT_PATH.read_text(encoding="utf-8")
        except OSError as e:
            logger.error("OmegaAuditor: Failed to read snapshot: %s", e)
            return []

        prompt_text = f"""
AUDIT MISSION: Identify semantic contradictions between a CANDIDATE DECISION and the existing CORTEX SNAPSHOT.

---
CANDIDATE DECISION (Project: {project}):
"{content}"
---

SNAPSHOT CONTEXT:
{snapshot_text}

---
INSTRUCTIONS:
1. Analyze if the CANDIDATE DECISION contradicts any established AXIOM, PATTERN, or past DECISION in the snapshot.
2. Focus on SEMANTIC conflicts (logic, security, architecture, aesthetics) even if keywords don't match.
3. If no contradiction is found, return "CLEAN".
4. If contradictions are found, return a JSON list of conflicts:
   [
     {{
       "fact_id": "CTX-XXXX",
       "summary": "Brief summary of the conflicting fact",
       "reasoning": "Detailed explanation of the semantic contradiction",
       "severity": "high/medium/low"
     }}
   ]
"""

        prompt = CortexPrompt(
            system_instruction="You are the CORTEX Omega Auditor. Your goal is absolute epistemic consistency.",
            working_memory=[{"role": "user", "content": prompt_text}],
            intent=IntentProfile.ARCHITECT,
            temperature=0.1,
        )

        try:
            response = await self._llm.invoke(prompt)
        except (ValueError, TypeError, KeyError, AssertionError) as e:
            logger.warning(
                "OmegaAuditor: Primary LLM failed (%s). Attempting API-Provider-OMEGA fallback.", e
            )
            response = None
            for fallback_llm in self._fallbacks:
                try:
                    response = await fallback_llm.invoke(prompt)
                    break
                except (ValueError, TypeError, KeyError, AssertionError) as fb_e:
                    logger.error(
                        "OmegaAuditor: Fallback LLM (%s) failed: %s",
                        fallback_llm.provider_name,
                        fb_e,
                    )
            if response is None:
                logger.error("OmegaAuditor: Deep audit failed and no fallback available.")
                return []

        assert response is not None
        if "CLEAN" in response.upper() and "[" not in response:
            return []

        # Basic JSON extraction
        import json
        import re

        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                return [OmegaConflict(**c) for c in data]
            except (ValueError, TypeError, KeyError, AssertionError) as parse_e:
                logger.error("OmegaAuditor: Failed to parse JSON: %s", parse_e)
                return []

        return []


async def run_omega_audit(content: str, project: str) -> list[OmegaConflict]:
    """Convenience entry point for the Omega Auditor."""
    import os

    provider = os.environ.get("CORTEX_PRIMARY_LLM", "ollama")
    auditor = OmegaAuditor(provider=provider)
    return await auditor.audit_decision(content, project)
