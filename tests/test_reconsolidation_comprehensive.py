# [C5-REAL] Exergy-Maximized

import uuid
import time
from unittest.mock import patch
import pytest
from legacy_research.memory.reconsolidation import (
    ReconsolidationTracker,
    ReconsolidationOutcome,
    LabilizationRecord,
    ConfirmationBiasDetector,
    RECONSOLIDATE_BOOST,
    IGNORE_DECAY,
    _CONFIRMATION_BIAS_THRESHOLD,
    _BIAS_MIN_EVENTS,
    _MAX_AUDIT_EVENTS_PER_ENGRAM,
)


def test_labilization_record_properties():
    """Test LabilizationRecord properties and expiration."""
    engram_id = "test_engram"
    record = LabilizationRecord(engram_id=engram_id, window_seconds=0.1)

    assert record.engram_id == engram_id
    assert record.is_labile is True
    assert record.is_expired is False
    assert record.age_seconds >= 0

    time.sleep(0.15)
    assert record.is_expired is True
    assert record.is_labile is False


def test_confirmation_bias_detector():
    """Test ConfirmationBiasDetector logic."""
    detector = ConfirmationBiasDetector()
    eid = "engram_1"

    # Not enough events
    assert detector.bias_score(eid) == -1.0
    assert detector.is_biased(eid) is False

    # Record some events
    for _ in range(_BIAS_MIN_EVENTS):
        detector.record(eid, ReconsolidationOutcome.CONFIRMED)

    assert detector.bias_score(eid) == 1.0
    assert detector.is_biased(eid) is True
    assert eid in detector.biased_engrams()

    # Add contradiction to lower score
    detector.record(eid, ReconsolidationOutcome.CONTRADICTED)
    # 5 confirms, 1 contradict = 5/6 = 0.8333
    assert detector.bias_score(eid) == 0.8333
    assert detector.is_biased(eid) is True

    # Add more contradictions
    for _ in range(5):
        detector.record(eid, ReconsolidationOutcome.CONTRADICTED)
    # 5 confirms, 6 contradicts = 5/11 = 0.4545
    assert detector.bias_score(eid) == 0.4545
    assert detector.is_biased(eid) is False


def test_tracker_basic_lifecycle():
    """Test standard access -> confirm/contradict flow."""
    tracker = ReconsolidationTracker()
    eid = "engram_42"

    # Access
    tracker.on_access(eid)
    assert tracker.labile_count == 1
    assert eid in tracker.labile_ids

    # Confirm
    boost = tracker.confirm(eid)
    assert boost == RECONSOLIDATE_BOOST
    assert tracker.labile_count == 0

    # Verify audit
    trail = tracker.audit_trail(eid)
    assert len(trail) == 1
    assert trail[0].outcome == ReconsolidationOutcome.CONFIRMED
    assert trail[0].energy_delta == RECONSOLIDATE_BOOST

    # Access again
    tracker.on_access(eid, previous_version=trail[0].version_id)
    assert tracker.labile_count == 1

    # Contradict
    boost = tracker.contradict(eid)
    assert boost == 0.0
    assert tracker.labile_count == 0

    # Verify audit chain
    trail = tracker.audit_trail(eid)
    assert len(trail) == 2
    assert trail[1].outcome == ReconsolidationOutcome.CONTRADICTED
    assert trail[1].parent_version == trail[0].version_id


def test_tracker_sweep_expiration():
    """Test that sweep() handles expired records."""
    tracker = ReconsolidationTracker(window_seconds=0.01)
    eid = "expired_engram"

    tracker.on_access(eid)
    time.sleep(0.02)

    expired = tracker.sweep()
    assert len(expired) == 1
    assert expired[0] == (eid, -IGNORE_DECAY)
    assert tracker.labile_count == 0

    trail = tracker.audit_trail(eid)
    assert len(trail) == 1
    assert trail[0].outcome == ReconsolidationOutcome.IGNORED
    assert trail[0].energy_delta == -IGNORE_DECAY


def test_tracker_audit_capping():
    """Test that audit trail is capped per engram."""
    tracker = ReconsolidationTracker()
    eid = "chatty_engram"

    for _ in range(_MAX_AUDIT_EVENTS_PER_ENGRAM + 10):
        tracker.on_access(eid)
        tracker.confirm(eid)

    trail = tracker.audit_trail(eid)
    assert len(trail) == _MAX_AUDIT_EVENTS_PER_ENGRAM
    assert tracker.total_events == _MAX_AUDIT_EVENTS_PER_ENGRAM


def test_tracker_concurrent_engrams():
    """Test multiple engrams in labile state simultaneously."""
    tracker = ReconsolidationTracker()
    eids = [f"e{i}" for i in range(10)]

    for eid in eids:
        tracker.on_access(eid)

    assert tracker.labile_count == 10

    tracker.confirm("e0")
    tracker.contradict("e1")

    assert tracker.labile_count == 8
    assert len(tracker.all_audit_events()) == 2


def test_tracker_error_recovery():
    """Test resolution of non-existent or already resolved engrams."""
    tracker = ReconsolidationTracker()

    # Confirm unknown
    assert tracker.confirm("ghost") == 0.0
    # Contradict unknown
    assert tracker.contradict("ghost") == 0.0

    tracker.on_access("e1")
    tracker.confirm("e1")
    # Confirm again
    assert tracker.confirm("e1") == 0.0

    assert tracker.total_events == 1


def test_tracker_dream_sweep():
    """Test dream_sweep integration."""
    tracker = ReconsolidationTracker(window_seconds=0.01)
    tracker.on_access("e1")
    time.sleep(0.02)

    results = tracker.dream_sweep()
    assert len(results) == 1
    assert results[0][0] == "e1"


def test_tracker_bias_integration():
    """Test bias reporting through tracker."""
    tracker = ReconsolidationTracker()
    eid = "biased_one"

    for _ in range(_BIAS_MIN_EVENTS):
        tracker.on_access(eid)
        tracker.confirm(eid)

    # Tracker has biased_engrams() method
    assert eid in tracker.biased_engrams()
    report = tracker.confirmation_bias_report()
    assert report[eid] == 1.0
