# [C5-REAL] Exergy-Maximized
"""Tests for the B2B Messaging FSM."""

import pytest

from cortex.extensions.sales_b2b.messaging_flow import MessagingFSM, MessagingStage


def test_fsm_valid_transitions():
    """Verify deterministic state transitions."""
    fsm = MessagingFSM()
    
    assert fsm.can_transition(MessagingStage.PROSPECTING, MessagingStage.DEEP_RESEARCH)
    assert not fsm.can_transition(MessagingStage.PROSPECTING, MessagingStage.MEETING_BOOKED)
    assert fsm.can_transition(MessagingStage.OUTREACH_DAY_1, MessagingStage.MEETING_BOOKED)


def test_fsm_advance_logic():
    """Verify the advance_stage logic based on events."""
    fsm = MessagingFSM()
    
    # Positive reply jumps straight to Meeting Booked
    stage = fsm.advance_stage(MessagingStage.OUTREACH_DAY_1, {"reply_positive": True})
    assert stage == MessagingStage.MEETING_BOOKED
    
    # Negative reply jumps straight to Disqualified
    stage = fsm.advance_stage(MessagingStage.PROSPECTING, {"reply_negative": True})
    assert stage == MessagingStage.DISQUALIFIED
    
    # Normal cadence
    stage = fsm.advance_stage(MessagingStage.OUTREACH_DAY_1, {"days_since_last_contact": 3})
    assert stage == MessagingStage.FOLLOW_UP_DAY_3
    
    stage = fsm.advance_stage(MessagingStage.FOLLOW_UP_DAY_3, {"days_since_last_contact": 4})
    assert stage == MessagingStage.FOLLOW_UP_DAY_7
