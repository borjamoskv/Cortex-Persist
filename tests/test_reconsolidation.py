"""CORTEX v8.0 — Reconsolidation v2 Test Suite.

Sprint 2: First test coverage for the reconsolidation module.
Previously: zero tests. After: full coverage of all paths.

Tests cover:
  - LabilizationRecord lifecycle (expired, labile, version tracking)
  - ReconsolidationTracker confirm / contradict / sweep / dream_sweep
  - Audit trail integrity (version chain, event ordering)
  - ConfirmationBiasDetector (threshold detection)
  - Energy delta correctness
  - Boundary conditions (double-resolve, post-expiry operations)
"""

from __future__ import annotations

import time

import pytest

from cortex.memory.reconsolidation import (
    DEFAULT_LABILE_WINDOW_S,
    IGNORE_DECAY,
    RECONSOLIDATE_BOOST,
    ConfirmationBiasDetector,
    LabilizationRecord,
    ReconsolidationEvent,
    ReconsolidationOutcome,
    ReconsolidationTracker,
)

# ─── Helpers ──────────────────────────────────────────────────────────


def _tiny_window_tracker(window_seconds: float = 0.01) -> ReconsolidationTracker:
    """Tracker with a near-zero window for expiry tests without sleeping."""
    return ReconsolidationTracker(window_seconds=window_seconds)


# ═══════════════════════════════════════════════════════════════════════
# LabilizationRecord
# ═══════════════════════════════════════════════════════════════════════


class TestLabilizationRecord:
    def test_default_is_labile(self):
        """Fresh record is labile immediately."""
        record = LabilizationRecord(engram_id="e1")
        assert record.is_labile is True
        assert record.is_expired is False

    def test_has_version_id(self):
        """v2: Record ships with a unique version_id."""
        r1 = LabilizationRecord(engram_id="e1")
        r2 = LabilizationRecord(engram_id="e2")
        assert r1.version_id != r2.version_id
        assert len(r1.version_id) == 36  # UUID4 format

    def test_parent_version_defaults_to_none(self):
        """First access has no parent version."""
        record = LabilizationRecord(engram_id="e1")
        assert record.parent_version is None

    def test_parent_version_can_be_set(self):
        """Subsequent accesses can link to previous version."""
        record = LabilizationRecord(engram_id="e1", parent_version="prev-uuid")
        assert record.parent_version == "prev-uuid"

    def test_confirmed_not_labile(self):
        """Confirmed record is no longer labile even if window is open."""
        record = LabilizationRecord(engram_id="e1")
        record.confirmed = True
        assert record.is_labile is False

    def test_contradicted_not_labile(self):
        """Contradicted record is no longer labile."""
        record = LabilizationRecord(engram_id="e1")
        record.contradicted = True
        assert record.is_labile is False

    def test_expired_not_labile(self):
        """Expired record is not labile."""
        record = LabilizationRecord(engram_id="e1", window_seconds=0.001)
        time.sleep(0.002)
        assert record.is_expired is True
        assert record.is_labile is False

    def test_age_seconds_is_positive(self):
        """age_seconds grows over time."""
        record = LabilizationRecord(engram_id="e1")
        time.sleep(0.01)
        assert record.age_seconds > 0.0


# ═══════════════════════════════════════════════════════════════════════
# ReconsolidationEvent
# ═══════════════════════════════════════════════════════════════════════


class TestReconsolidationEvent:
    def test_frozen(self):
        """Events are immutable once created."""
        event = ReconsolidationEvent(
            event_id="ev-1",
            engram_id="e1",
            version_id="v1",
            parent_version=None,
            outcome=ReconsolidationOutcome.CONFIRMED,
            energy_delta=RECONSOLIDATE_BOOST,
            resolved_at=time.time(),
            labile_duration_s=1.0,
        )
        with pytest.raises(AttributeError):
            event.energy_delta = 0.0  # type: ignore[misc]

    def test_outcome_values(self):
        """All three outcome variants exist."""
        outcomes = {o.value for o in ReconsolidationOutcome}
        assert outcomes == {"confirmed", "contradicted", "ignored"}


# ═══════════════════════════════════════════════════════════════════════
# ReconsolidationTracker — Core Operations
# ═══════════════════════════════════════════════════════════════════════


class TestTrackerConfirm:
    def test_confirm_returns_boost(self):
        """Confirming a labile engram returns RECONSOLIDATE_BOOST."""
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        delta = tracker.confirm("e1")
        assert delta == pytest.approx(RECONSOLIDATE_BOOST)

    def test_confirm_clears_labile(self):
        """After confirm, engram is no longer tracked as labile."""
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        tracker.confirm("e1")
        assert "e1" not in tracker.labile_ids

    def test_confirm_unknown_engram_returns_zero(self):
        """Confirming a non-labile engram returns 0 — no phantom boosts."""
        tracker = ReconsolidationTracker()
        assert tracker.confirm("ghost") == 0.0

    def test_confirm_after_expiry_returns_zero(self):
        """Confirming after window expired returns 0."""
        tracker = _tiny_window_tracker()
        tracker.on_access("e1")
        time.sleep(0.02)  # Let window expire
        assert tracker.confirm("e1") == 0.0

    def test_double_confirm_second_is_zero(self):
        """Double-confirming the same engram: second is a no-op."""
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        first = tracker.confirm("e1")
        second = tracker.confirm("e1")
        assert first == pytest.approx(RECONSOLIDATE_BOOST)
        assert second == 0.0


class TestTrackerContradict:
    def test_contradict_returns_neutral(self):
        """Contradicting returns 0 — energy neutral."""
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        delta = tracker.contradict("e1")
        assert delta == 0.0

    def test_contradict_clears_labile(self):
        """Contradicted engram is removed from labile tracking."""
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        tracker.contradict("e1")
        assert "e1" not in tracker.labile_ids

    def test_contradict_unknown_returns_zero(self):
        tracker = ReconsolidationTracker()
        assert tracker.contradict("ghost") == 0.0

    def test_contradict_after_expiry_returns_zero(self):
        tracker = _tiny_window_tracker()
        tracker.on_access("e1")
        time.sleep(0.02)
        assert tracker.contradict("e1") == 0.0


class TestTrackerSweep:
    def test_sweep_decays_expired_engrams(self):
        """Sweep returns (engram_id, -IGNORE_DECAY) for expired engrams."""
        tracker = _tiny_window_tracker()
        tracker.on_access("e1")
        tracker.on_access("e2")
        time.sleep(0.02)

        results = tracker.sweep()
        engram_ids = {r[0] for r in results}
        deltas = {r[1] for r in results}

        assert "e1" in engram_ids
        assert "e2" in engram_ids
        # All deltas should be -IGNORE_DECAY
        assert all(d == pytest.approx(-IGNORE_DECAY) for d in deltas)

    def test_sweep_does_not_touch_confirmed_engrams(self):
        """Confirmed engrams are not swept."""
        tracker = _tiny_window_tracker()
        tracker.on_access("e1")
        tracker.confirm("e1")
        time.sleep(0.02)

        results = tracker.sweep()
        assert not any(r[0] == "e1" for r in results)

    def test_sweep_clears_expired_from_labile(self):
        """After sweep, expired engrams are gone from labile_ids."""
        tracker = _tiny_window_tracker()
        tracker.on_access("e1")
        time.sleep(0.02)
        tracker.sweep()
        assert "e1" not in tracker.labile_ids

    def test_sweep_does_not_touch_still_labile_engrams(self):
        """Engrams inside their window are not swept."""
        tracker = ReconsolidationTracker(window_seconds=60.0)
        tracker.on_access("e_fresh")
        results = tracker.sweep()
        assert not any(r[0] == "e_fresh" for r in results)
        assert "e_fresh" in tracker.labile_ids

    def test_dream_sweep_equivalent_to_sweep(self):
        """dream_sweep() produces the same results as sweep()."""
        t1 = _tiny_window_tracker()
        t2 = _tiny_window_tracker()
        t1.on_access("e1")
        t2.on_access("e1")
        time.sleep(0.02)

        r1 = t1.sweep()
        r2 = t2.dream_sweep()

        assert len(r1) == len(r2)
        assert r1[0][1] == r2[0][1]  # Same energy delta


# ═══════════════════════════════════════════════════════════════════════
# Audit Trail — Sprint 2 Core Feature
# ═══════════════════════════════════════════════════════════════════════


class TestAuditTrail:
    def test_confirm_creates_audit_event(self):
        """Each confirm creates a CONFIRMED event in the trail."""
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        tracker.confirm("e1")

        trail = tracker.audit_trail("e1")
        assert len(trail) == 1
        assert trail[0].outcome == ReconsolidationOutcome.CONFIRMED
        assert trail[0].energy_delta == pytest.approx(RECONSOLIDATE_BOOST)

    def test_contradict_creates_audit_event(self):
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        tracker.contradict("e1")

        trail = tracker.audit_trail("e1")
        assert len(trail) == 1
        assert trail[0].outcome == ReconsolidationOutcome.CONTRADICTED
        assert trail[0].energy_delta == 0.0

    def test_sweep_creates_ignored_event(self):
        tracker = _tiny_window_tracker()
        tracker.on_access("e1")
        time.sleep(0.02)
        tracker.sweep()

        trail = tracker.audit_trail("e1")
        assert len(trail) == 1
        assert trail[0].outcome == ReconsolidationOutcome.IGNORED
        assert trail[0].energy_delta == pytest.approx(-IGNORE_DECAY)

    def test_audit_event_has_unique_ids(self):
        """Each event has a unique event_id and version_id."""
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        tracker.confirm("e1")
        tracker.on_access("e1", previous_version="v-prev")
        tracker.contradict("e1")

        trail = tracker.audit_trail("e1")
        assert len(trail) == 2
        event_ids = {e.event_id for e in trail}
        version_ids = {e.version_id for e in trail}
        assert len(event_ids) == 2  # All unique
        assert len(version_ids) == 2

    def test_audit_event_has_parent_version(self):
        """v2: Events carry the parent_version from the record."""
        tracker = ReconsolidationTracker()
        tracker.on_access("e1", previous_version="ancestor-uuid")
        tracker.confirm("e1")

        trail = tracker.audit_trail("e1")
        assert trail[0].parent_version == "ancestor-uuid"

    def test_unknown_engram_returns_empty_trail(self):
        tracker = ReconsolidationTracker()
        assert tracker.audit_trail("nonexistent") == []

    def test_all_audit_events_ordered_chronologically(self):
        """all_audit_events() is sorted by resolved_at ascending."""
        tracker = ReconsolidationTracker()
        for i in range(5):
            eid = f"e{i}"
            tracker.on_access(eid)
            if i % 2 == 0:
                tracker.confirm(eid)
            else:
                tracker.contradict(eid)

        all_events = tracker.all_audit_events()
        timestamps = [e.resolved_at for e in all_events]
        assert timestamps == sorted(timestamps)

    def test_audit_trail_bounded(self):
        """Audit trail per engram is bounded (no unbounded growth)."""
        from cortex.memory.reconsolidation import _MAX_AUDIT_EVENTS_PER_ENGRAM

        tracker = _tiny_window_tracker(window_seconds=0.001)
        # Generate overflow events
        for _ in range(_MAX_AUDIT_EVENTS_PER_ENGRAM + 20):
            tracker.on_access("e1")
            time.sleep(0.002)
            tracker.sweep()  # Each sweep generates an IGNORED event

        trail = tracker.audit_trail("e1")
        assert len(trail) <= _MAX_AUDIT_EVENTS_PER_ENGRAM

    def test_total_events_count(self):
        """total_events property sums all audit events correctly."""
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        tracker.confirm("e1")
        tracker.on_access("e2")
        tracker.contradict("e2")

        assert tracker.total_events == 2


# ═══════════════════════════════════════════════════════════════════════
# Confirmation Bias Detector
# ═══════════════════════════════════════════════════════════════════════


class TestConfirmationBiasDetector:
    def test_insufficient_data_returns_negative(self):
        """Below minimum events, bias_score returns -1.0."""
        detector = ConfirmationBiasDetector()
        detector.record("e1", ReconsolidationOutcome.CONFIRMED)
        # Default MIN is 5; we only have 1 → insufficient
        assert detector.bias_score("e1") == -1.0

    def test_all_confirmed_high_bias(self):
        """100% confirms = maximum bias score."""
        from cortex.memory.reconsolidation import _BIAS_MIN_EVENTS

        detector = ConfirmationBiasDetector()
        for _ in range(_BIAS_MIN_EVENTS):
            detector.record("e1", ReconsolidationOutcome.CONFIRMED)

        assert detector.bias_score("e1") == pytest.approx(1.0)
        assert detector.is_biased("e1") is True

    def test_mixed_outcomes_low_bias(self):
        """Mix of outcomes = low bias score."""
        from cortex.memory.reconsolidation import _BIAS_MIN_EVENTS

        detector = ConfirmationBiasDetector()
        for _ in range(_BIAS_MIN_EVENTS):
            detector.record("e1", ReconsolidationOutcome.CONFIRMED)
        for _ in range(_BIAS_MIN_EVENTS * 3):
            detector.record("e1", ReconsolidationOutcome.IGNORED)

        score = detector.bias_score("e1")
        assert score < 0.4
        assert detector.is_biased("e1") is False

    def test_biased_engrams_list(self):
        """biased_engrams() returns only those above threshold."""
        from cortex.memory.reconsolidation import _BIAS_MIN_EVENTS

        detector = ConfirmationBiasDetector()
        # e1: biased
        for _ in range(_BIAS_MIN_EVENTS):
            detector.record("e1", ReconsolidationOutcome.CONFIRMED)
        # e2: healthy
        for _ in range(_BIAS_MIN_EVENTS):
            detector.record("e2", ReconsolidationOutcome.IGNORED)

        biased = detector.biased_engrams()
        assert "e1" in biased
        assert "e2" not in biased

    def test_unknown_engram_not_biased(self):
        detector = ConfirmationBiasDetector()
        assert detector.is_biased("ghost") is False

    def test_report_only_includes_sufficient_data(self):
        """report() only shows engrams with enough events."""
        from cortex.memory.reconsolidation import _BIAS_MIN_EVENTS

        detector = ConfirmationBiasDetector()
        # Enough data
        for _ in range(_BIAS_MIN_EVENTS):
            detector.record("e1", ReconsolidationOutcome.CONFIRMED)
        # Not enough data
        detector.record("e2", ReconsolidationOutcome.CONFIRMED)

        report = detector.report()
        assert "e1" in report
        assert "e2" not in report


# ═══════════════════════════════════════════════════════════════════════
# Tracker Integration: bias propagation
# ═══════════════════════════════════════════════════════════════════════


class TestTrackerBiasIntegration:
    def test_tracker_detects_biased_engram_after_repeated_confirms(self):
        """Tracker flags confirmation bias after repeated confirms."""
        from cortex.memory.reconsolidation import _BIAS_MIN_EVENTS

        tracker = ReconsolidationTracker()
        for _ in range(_BIAS_MIN_EVENTS):
            tracker.on_access("e1")
            tracker.confirm("e1")

        assert "e1" in tracker.biased_engrams()

    def test_confirmation_bias_report_has_float_scores(self):
        """confirmation_bias_report() returns float scores."""
        from cortex.memory.reconsolidation import _BIAS_MIN_EVENTS

        tracker = ReconsolidationTracker()
        for _ in range(_BIAS_MIN_EVENTS):
            tracker.on_access("e1")
            tracker.confirm("e1")

        report = tracker.confirmation_bias_report()
        assert "e1" in report
        assert isinstance(report["e1"], float)

    def test_repr_shows_tracker_state(self):
        """__repr__ includes relevant state."""
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        r = repr(tracker)
        assert "labile=1" in r
        assert "total_events=0" in r


# ═══════════════════════════════════════════════════════════════════════
# Properties and Misc
# ═══════════════════════════════════════════════════════════════════════


class TestTrackerProperties:
    def test_labile_count_accurate(self):
        tracker = ReconsolidationTracker()
        assert tracker.labile_count == 0
        tracker.on_access("e1")
        assert tracker.labile_count == 1
        tracker.on_access("e2")
        assert tracker.labile_count == 2
        tracker.confirm("e1")
        assert tracker.labile_count == 1

    def test_labile_ids_accurate(self):
        tracker = ReconsolidationTracker()
        tracker.on_access("e1")
        tracker.on_access("e2")
        ids = set(tracker.labile_ids)
        assert "e1" in ids
        assert "e2" in ids
        tracker.contradict("e2")
        assert "e2" not in tracker.labile_ids

    def test_default_window_constant(self):
        """DEFAULT_LABILE_WINDOW_S is 5 minutes."""
        assert DEFAULT_LABILE_WINDOW_S == 300.0

    def test_energy_constants_sensible(self):
        """Energy constants are in valid ranges."""
        assert 0.0 < RECONSOLIDATE_BOOST < 1.0
        assert 0.0 < IGNORE_DECAY < 1.0
