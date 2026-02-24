"""CORTEX Agents — handoff, neural, system prompts and pitch arsenal."""

from __future__ import annotations

from cortex.agents.pitches import (
    PITCH_COMPLIANCE_DIRECTOR,
    PITCH_CTO_SKEPTIC,
    PITCH_JOURNALIST,
    PITCH_MEMO_DEV,
    PITCH_OS_CONTRIBUTOR,
    PITCH_VC_FOLLOWUP,
)
from cortex.agents.system_prompt import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_MEDIUM,
    SYSTEM_PROMPT_SHORT,
)

__all__ = [
    # System prompts
    "SYSTEM_PROMPT",
    "SYSTEM_PROMPT_MEDIUM",
    "SYSTEM_PROMPT_SHORT",
    # Pitches
    "PITCH_CTO_SKEPTIC",
    "PITCH_MEMO_DEV",
    "PITCH_OS_CONTRIBUTOR",
    "PITCH_COMPLIANCE_DIRECTOR",
    "PITCH_VC_FOLLOWUP",
    "PITCH_JOURNALIST",
]
