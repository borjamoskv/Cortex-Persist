"""
CORTEX — Omega Auditor (Axiom 20 + Massive Context).

Deep semantic contradiction detection using Gemini 3 Pro (1M context).
This guard audits new decisions against the ENTIRE system snapshot.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from dataclasses import dataclass

from cortex.llm.provider import LLMProvider
from cortex.llm.router import CortexPrompt, IntentProfile

logger = logging.getLogger("cortex.guards.omega")

SNAPSHOT_PATH = Path.home() / ".cortex" / "context-snapshot.md"

@dataclass(frozen=True, slots=True)
class OmegaConflict:
    fact_id: str | None
    summary: str
    reasoning: str
    severity: str  # 'low' | 'medium' | 'high'

class OmegaAuditor:
    """Sovereign Auditor for deep semantic health."""

    def __init__(self, provider: str = "gemini"):
        self._llm = LLMProvider(provider=provider)

    async def audit_decision(self, content: str, project: str) -> list[OmegaConflict]:
        """Audit a candidate decision against the massive context of the snapshot."""
        if not SNAPSHOT_PATH.exists():
            logger.warning("OmegaAuditor: Snapshot missing at %s. Skipping deep audit.", SNAPSHOT_PATH)
            return []

        try:
            snapshot_text = SNAPSHOT_PATH.read_text(encoding="utf-8")
        except Exception as e:
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
            temperature=0.1
        )

        try:
            response = await self._llm.invoke(prompt)
            if "CLEAN" in response.upper() and "[" not in response:
                return []
            
            # Basic JSON extraction
            import json
            import re
            
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return [OmegaConflict(**c) for c in data]
            
            return []
        except Exception as e:
            logger.error("OmegaAuditor: Deep audit failed: %s", e)
            return []

async def run_omega_audit(content: str, project: str) -> list[OmegaConflict]:
    """Convenience entry point for the Omega Auditor."""
    auditor = OmegaAuditor()
    return await auditor.audit_decision(content, project)
