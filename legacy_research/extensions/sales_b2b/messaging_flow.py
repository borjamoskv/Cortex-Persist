# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - B2B Messaging Flow FSM.

Deterministic State Machine for managing B2B outbound sequences.
Transitions are strictly evaluated to prevent infinite loops and
ensure causal compliance with the Ledger.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger("cortex.extensions.sales_b2b.messaging_flow")


class MessagingStage(str, Enum):
    """Deterministic states for B2B messaging."""
    PROSPECTING = "PROSPECTING"
    DEEP_RESEARCH = "DEEP_RESEARCH"
    OUTREACH_DAY_1 = "OUTREACH_DAY_1"
    FOLLOW_UP_DAY_3 = "FOLLOW_UP_DAY_3"
    FOLLOW_UP_DAY_7 = "FOLLOW_UP_DAY_7"
    MEETING_BOOKED = "MEETING_BOOKED"
    DISQUALIFIED = "DISQUALIFIED"
    UNRESPONSIVE = "UNRESPONSIVE"


class MessagingFSM:
    """Finite State Machine for outbound messaging."""

    def __init__(self) -> None:
        # Define allowed transitions for strict invariant checking
        self._allowed_transitions = {
            MessagingStage.PROSPECTING: {MessagingStage.DEEP_RESEARCH, MessagingStage.DISQUALIFIED},
            MessagingStage.DEEP_RESEARCH: {MessagingStage.OUTREACH_DAY_1, MessagingStage.DISQUALIFIED},
            MessagingStage.OUTREACH_DAY_1: {
                MessagingStage.FOLLOW_UP_DAY_3,
                MessagingStage.MEETING_BOOKED,
                MessagingStage.DISQUALIFIED,
            },
            MessagingStage.FOLLOW_UP_DAY_3: {
                MessagingStage.FOLLOW_UP_DAY_7,
                MessagingStage.MEETING_BOOKED,
                MessagingStage.DISQUALIFIED,
            },
            MessagingStage.FOLLOW_UP_DAY_7: {
                MessagingStage.UNRESPONSIVE,
                MessagingStage.MEETING_BOOKED,
                MessagingStage.DISQUALIFIED,
            },
            MessagingStage.MEETING_BOOKED: set(),  # Terminal
            MessagingStage.DISQUALIFIED: set(),    # Terminal
            MessagingStage.UNRESPONSIVE: set(),    # Terminal
        }

    def can_transition(self, current: MessagingStage, next_stage: MessagingStage) -> bool:
        """Verify if a transition is valid under the current topology."""
        return next_stage in self._allowed_transitions.get(current, set())

    def advance_stage(self, current: MessagingStage, event_data: dict[str, Any]) -> MessagingStage:
        """
        Advance the state machine based on the current stage and event data.
        This provides deterministic routing for the Deep Research Agent.
        """
        # Terminal states
        if current in {MessagingStage.MEETING_BOOKED, MessagingStage.DISQUALIFIED, MessagingStage.UNRESPONSIVE}:
            return current
            
        is_reply_positive = event_data.get("reply_positive", False)
        is_reply_negative = event_data.get("reply_negative", False)
        days_since_last = event_data.get("days_since_last_contact", 0)
        
        if is_reply_positive:
            return MessagingStage.MEETING_BOOKED
        if is_reply_negative:
            return MessagingStage.DISQUALIFIED
            
        if current == MessagingStage.PROSPECTING:
            return MessagingStage.DEEP_RESEARCH
            
        if current == MessagingStage.DEEP_RESEARCH:
            if event_data.get("research_complete", False):
                return MessagingStage.OUTREACH_DAY_1
            return current
            
        if current == MessagingStage.OUTREACH_DAY_1 and days_since_last >= 3:
            return MessagingStage.FOLLOW_UP_DAY_3
            
        if current == MessagingStage.FOLLOW_UP_DAY_3 and days_since_last >= 4:  # Day 7 is 4 days after Day 3
            return MessagingStage.FOLLOW_UP_DAY_7
            
        if current == MessagingStage.FOLLOW_UP_DAY_7 and days_since_last >= 7:
            return MessagingStage.UNRESPONSIVE

        # No transition conditions met
        return current
