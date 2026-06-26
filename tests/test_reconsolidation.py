# C5-REAL: Local unit tests for CORTEX reconsolidation engine
import time
import pytest
from unittest.mock import patch

from cortex.memory.reconsolidation import (
    ReconsolidationTracker,
    ConfirmationBiasDetector,
    LabilizationRecord,
    ReconsolidationOutcome,
    ReconsolidationEvent,
    DEFAULT_LABILE_WINDOW_S,
    IGNORE_DECAY,
    RECONSOLIDATE_BOOST,
)

# ─── LabilizationRecord Tests ─────────────────────────────────────────

def test_labilization_record_initial_state():
    """Test initial attributes of a newly created LabilizationRecord."""
    record = LabilizationRecord(engram_id="engram_1", parent_version="v0")
    assert record.engram_id == "engram_1"
    assert record.parent_version == "v0"
    assert record.confirmed is False
    assert record.contradicted is False
    assert len(record.version_id) > 0
    assert record.is_labile is True
    assert record.is_expired is False

def test_labilization_record_expiration():
    """Test LabilizationRecord lifecycle expiration and status."""
    record = LabilizationRecord(engram_id="engram_1", window_seconds=0.1)
    assert record.is_labile is True
    assert record.is_expired is False
    
    # Simulate expiration by mocking time or sleeping
    time.sleep(0.15)
    assert record.is_expired is True
    assert record.is_labile is False
    assert record.age_seconds >= 0.1

def test_labilization_record_resolved_not_labile():
    """Test that confirmed or contradicted records are not labile."""
    record = LabilizationRecord(engram_id="engram_1")
    
    record.confirmed = True
    assert record.is_labile is False
    
    record.confirmed = False
    record.contradicted = True
    assert record.is_labile is False

# ─── ConfirmationBiasDetector Tests ───────────────────────────────────

def test_confirmation_bias_detector_insufficient_data():
    """Test that bias score is -1.0 if there is insufficient data."""
    detector = ConfirmationBiasDetector()
    detector.record("engram_1", ReconsolidationOutcome.CONFIRMED)
    assert detector.bias_score("engram_1") == -1.0
    assert detector.is_biased("engram_1") is False

def test_confirmation_bias_detector_ratio():
    """Test bias score computation based on different outcome ratios."""
    detector = ConfirmationBiasDetector()
    
    # Record 5 events (minimum threshold for calculation)
    # 4 confirmed, 1 contradicted -> 0.8 ratio
    for _ in range(4):
        detector.record("engram_1", ReconsolidationOutcome.CONFIRMED)
    detector.record("engram_1", ReconsolidationOutcome.CONTRADICTED)
    
    assert detector.bias_score("engram_1") == 0.8
    assert detector.is_biased("engram_1") is True
    assert "engram_1" in detector.biased_engrams()
    assert detector.report() == {"engram_1": 0.8}

def test_confirmation_bias_detector_unbiased():
    """Test unbiased state with low confirmed ratio."""
    detector = ConfirmationBiasDetector()
    
    # 2 confirmed, 3 ignored -> 0.4 ratio
    for _ in range(2):
        detector.record("engram_1", ReconsolidationOutcome.CONFIRMED)
    for _ in range(3):
        detector.record("engram_1", ReconsolidationOutcome.IGNORED)
        
    assert detector.bias_score("engram_1") == 0.4
    assert detector.is_biased("engram_1") is False
    assert "engram_1" not in detector.biased_engrams()

# ─── ReconsolidationTracker Tests ──────────────────────────────────

def test_tracker_on_access():
    """Test engram access registration."""
    tracker = ReconconsolidationTracker = ReconsolidationTracker(window_seconds=10.0)
    record = tracker.on_access("engram_1", previous_version="v0")
    
    assert tracker.labile_count == 1
    assert tracker.labile_ids == ["engram_1"]
    assert record.engram_id == "engram_1"
    assert record.parent_version == "v0"
    assert record.window_seconds == 10.0

def test_tracker_confirm_success():
    """Test successful confirmation and energy boost application."""
    tracker = ReconsolidationTracker(window_seconds=10.0)
    tracker.on_access("engram_1", previous_version="v0")
    
    energy_delta = tracker.confirm("engram_1")
    assert energy_delta == RECONSOLIDATE_BOOST
    assert tracker.labile_count == 0
    
    # Audit trail validation
    trail = tracker.audit_trail("engram_1")
    assert len(trail) == 1
    assert trail[0].engram_id == "engram_1"
    assert trail[0].outcome == ReconsolidationOutcome.CONFIRMED
    assert trail[0].energy_delta == RECONSOLIDATE_BOOST
    assert trail[0].parent_version == "v0"

def test_tracker_confirm_nonexistent_or_expired():
    """Test confirmation attempt on nonexistent or expired engram."""
    tracker = ReconsolidationTracker(window_seconds=0.01)
    tracker.on_access("engram_1")
    time.sleep(0.02)
    
    # Expired confirm should return 0.0 energy delta
    energy_delta = tracker.confirm("engram_1")
    assert energy_delta == 0.0
    
    # Nonexistent confirm should return 0.0
    assert tracker.confirm("nonexistent") == 0.0

def test_tracker_contradict_success():
    """Test successful contradiction transition."""
    tracker = ReconsolidationTracker(window_seconds=10.0)
    tracker.on_access("engram_1", previous_version="v0")
    
    energy_delta = tracker.contradict("engram_1")
    assert energy_delta == 0.0  # Energy neutral
    assert tracker.labile_count == 0
    
    trail = tracker.audit_trail("engram_1")
    assert len(trail) == 1
    assert trail[0].outcome == ReconsolidationOutcome.CONTRADICTED
    assert trail[0].energy_delta == 0.0

def test_tracker_sweep_expired():
    """Test sweep processing for expired engrams."""
    tracker = ReconsolidationTracker(window_seconds=0.05)
    tracker.on_access("engram_1")
    tracker.on_access("engram_2")
    
    # Wait for expiration
    time.sleep(0.06)
    
    decayed = tracker.sweep()
    assert len(decayed) == 2
    assert ("engram_1", -IGNORE_DECAY) in decayed
    assert ("engram_2", -IGNORE_DECAY) in decayed
    assert tracker.labile_count == 0
    
    # Audit trail validation
    trail1 = tracker.audit_trail("engram_1")
    assert len(trail1) == 1
    assert trail1[0].outcome == ReconsolidationOutcome.IGNORED
    assert trail1[0].energy_delta == -IGNORE_DECAY

def test_tracker_dream_sweep():
    """Test that dream sweep matches sweep logic semantics."""
    tracker = ReconsolidationTracker(window_seconds=0.01)
    tracker.on_access("engram_1")
    time.sleep(0.02)
    
    results = tracker.dream_sweep()
    assert len(results) == 1
    assert results[0] == ("engram_1", -IGNORE_DECAY)

def test_tracker_audit_trail_truncation():
    """Test audit trail capping to avoid memory bloat."""
    tracker = ReconsolidationTracker(window_seconds=10.0)
    
    # Perform 55 accesses and confirmations to exceed _MAX_AUDIT_EVENTS_PER_ENGRAM (50)
    for _i in range(55):
        tracker.on_access("engram_1")
        tracker.confirm("engram_1")
        
    trail = tracker.audit_trail("engram_1")
    assert len(trail) == 50  # Capped at 50
    assert tracker.total_events == 50

def test_tracker_all_audit_events_ordering():
    """Test ordering of retrieve all audit events."""
    tracker = ReconsolidationTracker(window_seconds=10.0)
    
    tracker.on_access("engram_1")
    tracker.confirm("engram_1")
    tracker.on_access("engram_2")
    tracker.confirm("engram_2")
    
    events = tracker.all_audit_events()
    assert len(events) == 2
    assert events[0].resolved_at <= events[1].resolved_at

def test_tracker_bias_reporting():
    """Test integration of confirmation bias reporter in tracker."""
    tracker = ReconsolidationTracker(window_seconds=10.0)
    
    # Generate 5 confirmed events to trigger bias
    for _ in range(5):
        tracker.on_access("engram_biased")
        tracker.confirm("engram_biased")
        
    assert tracker.biased_engrams() == ["engram_biased"]
    assert tracker.confirmation_bias_report() == {"engram_biased": 1.0}
    
    # Representation check
    rep = repr(tracker)
    assert "labile=0" in rep
    assert "total_events=5" in rep
    assert "biased_engrams=1" in rep
