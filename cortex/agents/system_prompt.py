# [C5-REAL] Exergy-Maximized
"""CORTEX Agent - Sovereign System Prompt v2.1.

The definitive system prompt for any LLM operating as a CORTEX agent.
Loads modular markdown templates from cortex/agents/prompts/ to isolate
text from Python execution logic.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["SYSTEM_PROMPT", "SYSTEM_PROMPT_MEDIUM", "SYSTEM_PROMPT_SHORT"]

_PROMPTS_DIR = Path(__file__).parent / "prompts"

def _load_prompt(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return f"[CORTEX] WARNING: Missing prompt template {filename}"

SYSTEM_PROMPT_SHORT = _load_prompt("short.md")
SYSTEM_PROMPT_MEDIUM = _load_prompt("medium.md")
SYSTEM_PROMPT = _load_prompt("full.md")
