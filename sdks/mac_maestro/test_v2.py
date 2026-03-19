"""Tests for Mac-Maestro-Ω V5: Full Master Protocol verification."""

from __future__ import annotations

import os
import sys
import time
import unittest
from unittest import mock

_SDK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SDK_ROOT not in sys.path:
    sys.path.insert(0, _SDK_ROOT)

from mac_maestro.applescript import sanitize_applescript_string  # noqa: E402
from mac_maestro.matcher import find_best, find_elements  # noqa: E402
from mac_maestro.models import (  # noqa: E402
    ActionFailed,
    AXNodeSnapshot,
    ElementMatch,
    ResolvedTarget,
    UIAction,
)
from mac_maestro.resolver import resolve  # noqa: E402
from mac_maestro.trace import emit_trace  # noqa: E402
from mac_maestro.workflow import MacMaestroWorkflow, _backoff_sleep  # noqa: E402

# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _make_snapshot(**kwargs) -> AXNodeSnapshot:
    """Build an AXNodeSnapshot with sensible defaults."""
    defaults = dict(
        role=None,
        subrole=None,
        title=None,
        value=None,
        identifier=None,
        description=None,
        enabled=True,
        focused=False,
        position=None,
        size=None,
        path=(),
        children=[],
    )
    defaults.update(kwargs)
    return AXNodeSnapshot(**defaults)


def _make_tree() -> AXNodeSnapshot:
    """Build a realistic AX tree for testing."""
    return _make_snapshot(
        role="AXApplication",
        title="TestApp",
        path=(0,),
        children=[
            _make_snapshot(
                role="AXWindow",
                title="Main Window",
                path=(0, 0),
                position=(0.0, 0.0),
                size=(800.0, 600.0),
                children=[
                    _make_snapshot(
                        role="AXButton",
                        title="Save",
                        identifier="save-btn",
                        position=(100.0, 50.0),
                        size=(80.0, 30.0),
                        path=(0, 0, 0),
                    ),
                    _make_snapshot(
                        role="AXButton",
                        title="Cancel",
                        position=(200.0, 50.0),
                        size=(80.0, 30.0),
                        path=(0, 0, 1),
                    ),
                    _make_snapshot(
                        role="AXTextField",
                        title="Search",
                        description="Search field",
                        value="",
                        position=(300.0, 100.0),
                        size=(200.0, 24.0),
                        path=(0, 0, 2),
                    ),
                    _make_snapshot(
                        role="AXCheckBox",
                        title="Remember me",
                        value="0",
                        enabled=False,
                        position=(100.0, 150.0),
                        size=(120.0, 20.0),
                        path=(0, 0, 3),
                    ),
                    _make_snapshot(
                        role="AXMenuItem",
                        title="Export as PDF",
                        description="Export the document",
                        position=(50.0, 200.0),
                        size=(150.0, 22.0),
                        path=(0, 0, 4),
                    ),
                ],
            ),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Sanitizer Tests (V3)
# ═══════════════════════════════════════════════════════════════════


class TestSanitizer(unittest.TestCase):
    def test_basic_passthrough(self):
        self.assertEqual(sanitize_applescript_string("hello"), "hello")

    def test_double_quotes_escaped(self):
        self.assertIn('\\"', sanitize_applescript_string('say "hello"'))

    def test_backslash_escaped(self):
        self.assertIn("\\\\", sanitize_applescript_string("path\\to\\file"))

    def test_newline_escaped(self):
        result = sanitize_applescript_string("line1\nline2")
        self.assertNotIn("\n", result)

    def test_null_byte_stripped(self):
        result = sanitize_applescript_string("hello\x00world")
        self.assertNotIn("\x00", result)

    def test_control_chars_stripped(self):
        result = sanitize_applescript_string("hello\x07\x0eworld")
        self.assertEqual(result, "helloworld")


# ═══════════════════════════════════════════════════════════════════
# Action Ladder Tests (V2-V4)
# ═══════════════════════════════════════════════════════════════════


class TestActionLadder(unittest.TestCase):
    """Test with Target Lock mocked out (no AppKit in CI)."""

    def _make_workflow(self):
        wf = MacMaestroWorkflow("com.test")
        return wf

    @mock.patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_primary_success(self, mock_tl):
        wf = self._make_workflow()
        executed = []
        action = UIAction(
            name="click",
            vector="B",
            executor=lambda: executed.append("primary"),
        )
        result = wf.execute_action(action, apply_safety_gate=False)
        self.assertTrue(result)
        self.assertEqual(executed, ["primary"])

    @mock.patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_fallback_on_failure(self, mock_tl):
        wf = self._make_workflow()
        executed = []

        def fail():
            executed.append("fail")
            raise RuntimeError("AX unavailable")

        action = UIAction(
            name="click",
            vector="B",
            executor=fail,
            fallbacks=[
                UIAction(name="click_cg", vector="D", executor=lambda: executed.append("fallback"))
            ],
        )
        result = wf.execute_action(action, apply_safety_gate=False)
        self.assertTrue(result)
        self.assertEqual(executed, ["fail", "fallback"])

    @mock.patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_all_fallbacks_exhausted(self, mock_tl):
        wf = self._make_workflow()

        def fail():
            raise RuntimeError("always fails")

        action = UIAction(
            name="click",
            vector="B",
            executor=fail,
            fallbacks=[
                UIAction(name="click_cg", vector="D", executor=fail),
            ],
        )
        with self.assertRaises(ActionFailed):
            wf.execute_action(action, apply_safety_gate=False)

    @mock.patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_postcondition_failure_not_swallowed(self, mock_tl):
        wf = self._make_workflow()
        action = UIAction(
            name="type_text",
            vector="C",
            executor=lambda: None,
            postconditions=[lambda: False],
            idempotent=False,
        )
        with self.assertRaises(ActionFailed) as ctx:
            wf.execute_action(action, apply_safety_gate=False)
        self.assertIn("Postconditions failed", str(ctx.exception))

    @mock.patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_safety_gate_blocks_unsafe(self, mock_tl):
        wf = self._make_workflow()
        action = UIAction(
            name="delete",
            vector="A",
            executor=lambda: None,
            unsafe=False,
        )
        with self.assertRaises(PermissionError):
            wf.execute_action(action, apply_safety_gate=True)

    @mock.patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_precondition_failure(self, mock_tl):
        wf = self._make_workflow()
        action = UIAction(
            name="click",
            vector="B",
            preconditions=[lambda: False],
        )
        with self.assertRaises(ActionFailed) as ctx:
            wf.execute_action(action, apply_safety_gate=False)
        self.assertIn("Precondition", str(ctx.exception))


# ═══════════════════════════════════════════════════════════════════
# V4: Resolver Tests
# ═══════════════════════════════════════════════════════════════════


class TestResolver(unittest.TestCase):
    def test_resolve_applescript_script(self):
        action = UIAction(
            name="run_as",
            vector="A",
            target_query={"script": 'tell app "Finder" to activate'},
        )
        executor = resolve(action)
        self.assertTrue(callable(executor))

    def test_resolve_applescript_app_name(self):
        action = UIAction(
            name="open_app",
            vector="A",
            target_query={"app_name": "TextEdit"},
        )
        executor = resolve(action)
        self.assertTrue(callable(executor))

    def test_resolve_unknown_vector(self):
        action = UIAction(name="bad", vector="Z", target_query={})
        with self.assertRaises(ActionFailed) as ctx:
            resolve(action)
        self.assertIn("Unknown vector", str(ctx.exception))

    def test_resolve_with_resolved_target_coords(self):
        """Vector D should auto-extract coordinates from ResolvedTarget."""
        resolved = ResolvedTarget(
            pid=1234,
            app_name="Test",
            bundle_id="com.test",
            window_title="Main",
            element=None,
            position=(140.0, 65.0),
            resolution_method="ax_semantic",
            degraded=False,
        )
        action = UIAction(name="click", vector="D", target_query={})
        executor = resolve(action, resolved_target=resolved)
        self.assertTrue(callable(executor))


# ═══════════════════════════════════════════════════════════════════
# V4: Backoff + Sequence Tests
# ═══════════════════════════════════════════════════════════════════


class TestBackoff(unittest.TestCase):
    def test_backoff_increases(self):
        durations = []
        for attempt in range(1, 4):
            t0 = time.monotonic()
            _backoff_sleep(attempt)
            durations.append(time.monotonic() - t0)
        self.assertGreater(durations[1], durations[0] * 0.8)


class TestRunSequence(unittest.TestCase):
    @mock.patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_sequence_all_succeed(self, mock_tl):
        wf = MacMaestroWorkflow("com.test")
        log = []
        actions = [
            UIAction(name="s1", vector="A", executor=lambda: log.append(1)),
            UIAction(name="s2", vector="A", executor=lambda: log.append(2)),
        ]
        results = wf.run_sequence(actions, apply_safety_gate=False)
        self.assertEqual(results, [True, True])
        self.assertEqual(log, [1, 2])

    @mock.patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_sequence_abort_on_failure(self, mock_tl):
        wf = MacMaestroWorkflow("com.test")

        def fail():
            raise RuntimeError("boom")

        actions = [
            UIAction(name="ok", vector="A", executor=lambda: None),
            UIAction(name="boom", vector="A", executor=fail),
        ]
        with self.assertRaises(ActionFailed):
            wf.run_sequence(actions, apply_safety_gate=False, abort_on_failure=True)

    @mock.patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_sequence_continue_on_failure(self, mock_tl):
        wf = MacMaestroWorkflow("com.test")

        def fail():
            raise RuntimeError("boom")

        actions = [
            UIAction(name="ok", vector="A", executor=lambda: None),
            UIAction(name="boom", vector="A", executor=fail),
            UIAction(name="ok2", vector="A", executor=lambda: None),
        ]
        results = wf.run_sequence(
            actions,
            apply_safety_gate=False,
            abort_on_failure=False,
        )
        self.assertEqual(results, [True, False, True])


# ═══════════════════════════════════════════════════════════════════
# V5: Matcher Tests — Acceptance Test 2
# ═══════════════════════════════════════════════════════════════════


class TestMatcher(unittest.TestCase):
    """Semantic matcher over mock AX tree — Acceptance Test 2."""

    def setUp(self):
        self.tree = _make_tree()

    def test_find_button_by_role_and_title(self):
        results = find_elements(self.tree, role="AXButton", title="Save")
        self.assertGreater(len(results), 0)
        best = results[0]
        self.assertEqual(best.role, "AXButton")
        self.assertEqual(best.title, "Save")
        self.assertGreater(best.score, 0.5)
        self.assertIn("role=AXButton", best.reasons)

    def test_find_by_title_only(self):
        results = find_elements(self.tree, title="Cancel")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Cancel")

    def test_find_by_description(self):
        results = find_elements(
            self.tree,
            role="AXTextField",
            description="Search field",
        )
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].role, "AXTextField")

    def test_find_by_identifier(self):
        results = find_elements(
            self.tree,
            role="AXButton",
            identifier="save-btn",
        )
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].title, "Save")
        self.assertEqual(results[0].identifier, "save-btn")

    def test_fuzzy_substring_match(self):
        results = find_elements(
            self.tree,
            role="AXMenuItem",
            title="Export",
        )
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].role, "AXMenuItem")

    def test_fuzzy_case_insensitive(self):
        results = find_elements(
            self.tree,
            role="AXButton",
            title="save",
        )
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].title, "Save")

    def test_no_match_returns_empty(self):
        results = find_elements(self.tree, title="NonExistent")
        self.assertEqual(results, [])

    def test_empty_query_returns_empty(self):
        results = find_elements(self.tree)
        self.assertEqual(results, [])

    def test_find_best_returns_top(self):
        best = find_best(self.tree, role="AXButton", title="Save")
        self.assertIsNotNone(best)
        self.assertEqual(best.title, "Save")

    def test_find_best_returns_none(self):
        best = find_best(self.tree, title="Nonexistent")
        self.assertIsNone(best)

    def test_disabled_element_scores_lower(self):
        """Disabled checkbox should score lower than enabled button."""
        enabled_results = find_elements(self.tree, role="AXButton")
        disabled_results = find_elements(self.tree, role="AXCheckBox")
        if enabled_results and disabled_results:
            # Enabled elements get +0.05 bonus
            self.assertGreater(enabled_results[0].score, disabled_results[0].score)

    def test_position_extracted(self):
        results = find_elements(self.tree, role="AXButton", title="Save")
        self.assertIsNotNone(results[0].position)
        self.assertEqual(results[0].position, (100.0, 50.0))
        self.assertEqual(results[0].size, (80.0, 30.0))

    def test_element_match_center(self):
        results = find_elements(self.tree, role="AXButton", title="Save")
        match = results[0]
        center = match.center
        self.assertIsNotNone(center)
        self.assertAlmostEqual(center[0], 140.0)
        self.assertAlmostEqual(center[1], 65.0)

    def test_sorted_by_score_descending(self):
        results = find_elements(self.tree, role="AXButton")
        scores = [r.score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))


# ═══════════════════════════════════════════════════════════════════
# V5: Trace Degradation — Acceptance Test 3
# ═══════════════════════════════════════════════════════════════════


class TestTraceDegradation(unittest.TestCase):
    """Verify trace emits degraded=True when context is missing."""

    def test_trace_degraded_when_pid_is_none(self):
        trace = emit_trace(
            run_id="test-run",
            bundle_id="com.test",
            pid=None,
            frontmost=False,
            window_title=None,
            selected_vector="A",
            outcome="success",
            target_query={},
        )
        self.assertTrue(trace["degraded"])

    def test_trace_not_degraded_with_pid(self):
        trace = emit_trace(
            run_id="test-run",
            bundle_id="com.test",
            pid=12345,
            frontmost=True,
            window_title="Main",
            selected_vector="B",
            outcome="success",
            target_query={},
            resolution_method="ax_semantic",
            resolution_confidence=0.85,
            candidates_count=3,
        )
        self.assertFalse(trace["degraded"])
        self.assertEqual(trace["resolution_method"], "ax_semantic")
        self.assertEqual(trace["resolution_confidence"], 0.85)
        self.assertEqual(trace["candidates_count"], 3)

    def test_trace_has_resolution_fields(self):
        trace = emit_trace(
            run_id="test-run",
            bundle_id="com.test",
            pid=1,
            frontmost=True,
            window_title="Win",
            selected_vector="B",
            outcome="success",
            target_query={},
            resolution_method=None,
        )
        self.assertIn("resolution_method", trace)
        self.assertIn("resolution_confidence", trace)
        self.assertIn("candidates_count", trace)


# ═══════════════════════════════════════════════════════════════════
# V5: ResolvedTarget / ElementMatch unit tests
# ═══════════════════════════════════════════════════════════════════


class TestResolvedTarget(unittest.TestCase):
    def test_degraded_flag(self):
        rt = ResolvedTarget(
            pid=1,
            app_name="A",
            bundle_id="com.a",
            window_title=None,
            element=None,
            position=None,
            resolution_method="manual",
            degraded=True,
        )
        self.assertTrue(rt.degraded)

    def test_not_degraded(self):
        rt = ResolvedTarget(
            pid=1,
            app_name="A",
            bundle_id="com.a",
            window_title="Win",
            element=None,
            position=(100, 50),
            resolution_method="ax_semantic",
            degraded=False,
            confidence=0.9,
        )
        self.assertFalse(rt.degraded)
        self.assertEqual(rt.confidence, 0.9)


class TestElementMatchCenter(unittest.TestCase):
    def test_center_calculation(self):
        em = ElementMatch(
            ref=None,
            role="AXButton",
            subrole=None,
            title="OK",
            value=None,
            identifier=None,
            description=None,
            position=(100.0, 200.0),
            size=(60.0, 30.0),
            score=0.8,
            reasons=["role=AXButton"],
        )
        self.assertEqual(em.center, (130.0, 215.0))

    def test_center_none_without_position(self):
        em = ElementMatch(
            ref=None,
            role="AXButton",
            subrole=None,
            title="OK",
            value=None,
            identifier=None,
            description=None,
            position=None,
            size=None,
            score=0.5,
            reasons=[],
        )
        self.assertIsNone(em.center)


class TestG1DegradedTargetLock(unittest.TestCase):
    """G1: _target_lock must not silently swallow exceptions."""

    @mock.patch("mac_maestro.app_discovery.is_frontmost", side_effect=RuntimeError("AX dead"))
    @mock.patch("mac_maestro.app_discovery.get_pid", return_value=99)
    def test_degraded_target_set_on_exception(self, _pid, _fm):
        wf = MacMaestroWorkflow("com.example.Test")
        wf._target_lock()
        self.assertIsNotNone(wf._resolved)
        self.assertTrue(wf._resolved.degraded)


class TestG2RefPropagation(unittest.TestCase):
    """G2: AXUIElement ref flows from AXNodeSnapshot to ElementMatch."""

    def test_ref_propagated_through_find_elements(self):
        sentinel = object()
        node = AXNodeSnapshot(
            role="AXButton",
            subrole=None,
            title="OK",
            value=None,
            identifier=None,
            description=None,
            enabled=True,
            focused=None,
            position=(10, 20),
            size=(50, 30),
            path=(0,),
            children=[],
            _ref=sentinel,
        )
        matches = find_elements(node, role="AXButton")
        self.assertTrue(len(matches) > 0)
        self.assertIs(matches[0].ref, sentinel)

    def test_ref_is_none_when_snapshot_has_no_ref(self):
        node = AXNodeSnapshot(
            role="AXButton",
            subrole=None,
            title="OK",
            value=None,
            identifier=None,
            description=None,
            enabled=True,
            focused=None,
            position=(10, 20),
            size=(50, 30),
            path=(0,),
            children=[],
        )
        matches = find_elements(node, role="AXButton")
        self.assertTrue(len(matches) > 0)
        self.assertIsNone(matches[0].ref)


class TestG3ClickTargetInTrace(unittest.TestCase):
    """G3: emit_trace must accept and record click_target."""

    def test_click_target_present(self):
        data = emit_trace(
            run_id="r",
            bundle_id="b",
            pid=1,
            frontmost=True,
            window_title="w",
            selected_vector="B",
            outcome="success",
            target_query={},
            matched_element=None,
            precondition_results={},
            postcondition_results={},
            click_target=(100.5, 200.5),
        )
        self.assertEqual(data["click_target"], (100.5, 200.5))

    def test_click_target_default_none(self):
        data = emit_trace(
            run_id="r",
            bundle_id="b",
            pid=1,
            frontmost=True,
            window_title="w",
            selected_vector="B",
            outcome="success",
            target_query={},
            matched_element=None,
            precondition_results={},
            postcondition_results={},
        )
        self.assertIsNone(data["click_target"])


class TestG5CandidatesCount(unittest.TestCase):
    """G5: candidates_count must reflect real find_elements count."""

    def test_multiple_candidates_counted(self):
        children = [
            AXNodeSnapshot(
                role="AXButton",
                subrole=None,
                title=f"Btn{i}",
                value=None,
                identifier=None,
                description=None,
                enabled=True,
                focused=None,
                position=(10 * i, 20),
                size=(50, 30),
                path=(0, i),
                children=[],
            )
            for i in range(5)
        ]
        root = AXNodeSnapshot(
            role="AXGroup",
            subrole=None,
            title=None,
            value=None,
            identifier=None,
            description=None,
            enabled=True,
            focused=None,
            position=(0, 0),
            size=(500, 500),
            path=(0,),
            children=children,
        )
        matches = find_elements(root, role="AXButton")
        self.assertEqual(len(matches), 5)


# ═══════════════════════════════════════════════════════════════════
# NEW: Levenshtein Matcher Tests
# ═══════════════════════════════════════════════════════════════════


class TestLevenshteinMatcher(unittest.TestCase):
    """Tests for Levenshtein fuzzy matching in the semantic matcher."""

    def test_levenshtein_typo_match(self):
        """Typo 'Savee' should match 'Save' via Levenshtein."""
        from mac_maestro.matcher import (
            LEVENSHTEIN_SIMILARITY_THRESHOLD,
            _levenshtein_similarity,
        )

        sim = _levenshtein_similarity("savee", "save")
        self.assertGreaterEqual(sim, LEVENSHTEIN_SIMILARITY_THRESHOLD)

    def test_levenshtein_no_match_beyond_threshold(self):
        """Completely different strings should score below threshold."""
        from mac_maestro.matcher import (
            LEVENSHTEIN_SIMILARITY_THRESHOLD,
            _levenshtein_similarity,
        )

        sim = _levenshtein_similarity("xyzzy", "save")
        self.assertLess(sim, LEVENSHTEIN_SIMILARITY_THRESHOLD)

    def test_levenshtein_exact_is_1(self):
        """Identical strings should have similarity 1.0."""
        from mac_maestro.matcher import _levenshtein_similarity

        self.assertAlmostEqual(_levenshtein_similarity("hello", "hello"), 1.0)

    def test_levenshtein_empty(self):
        """Empty strings should have similarity 1.0 (both empty)."""
        from mac_maestro.matcher import _levenshtein_similarity

        self.assertAlmostEqual(_levenshtein_similarity("", ""), 1.0)

    def test_levenshtein_distance_basic(self):
        """Known edit distances."""
        from mac_maestro.matcher import _levenshtein_distance

        self.assertEqual(_levenshtein_distance("kitten", "sitting"), 3)
        self.assertEqual(_levenshtein_distance("", "abc"), 3)
        self.assertEqual(_levenshtein_distance("abc", "abc"), 0)

    def test_matcher_prefers_exact_over_fuzzy(self):
        """Exact match should score higher than Levenshtein match."""
        children = [
            _make_snapshot(role="AXButton", title="Save"),
            _make_snapshot(role="AXButton", title="Savee"),
        ]
        root = _make_snapshot(
            role="AXWindow",
            title="Test",
            position=(0, 0),
            size=(500, 500),
            path=(0,),
            children=children,
        )
        match = find_best(root, title="Save")
        self.assertIsNotNone(match)
        self.assertEqual(match.title, "Save")

    def test_score_field_levenshtein_fallback(self):
        """_score_field should return a Levenshtein score for near-matches."""
        from mac_maestro.matcher import _score_field

        score, reason = _score_field(
            "Settings",
            "Settins",
            0.4,
            0.2,
            0.15,
            True,
        )
        self.assertGreater(score, 0)
        self.assertIn("levenshtein", reason)


# ═══════════════════════════════════════════════════════════════════
# NEW: Hotkey Parsing Tests
# ═══════════════════════════════════════════════════════════════════


class TestHotkeyParsing(unittest.TestCase):
    """Tests for keyboard hotkey string parsing."""

    def test_parse_cmd_s(self):
        """'cmd+s' should parse to keycode 1 with command modifier."""
        from mac_maestro.keyboard import parse_hotkey

        keycode, modifiers = parse_hotkey("cmd+s")
        self.assertEqual(keycode, 1)  # 's' keycode
        self.assertIn("cmd", modifiers)

    def test_parse_cmd_shift_n(self):
        """'cmd+shift+n' should have two modifiers."""
        from mac_maestro.keyboard import parse_hotkey

        keycode, modifiers = parse_hotkey("cmd+shift+n")
        self.assertEqual(keycode, 45)  # 'n' keycode
        self.assertIn("cmd", modifiers)
        self.assertIn("shift", modifiers)

    def test_parse_plain_return(self):
        """'return' should parse to keycode 36 with no modifiers."""
        from mac_maestro.keyboard import parse_hotkey

        keycode, modifiers = parse_hotkey("return")
        self.assertEqual(keycode, 36)
        self.assertEqual(modifiers, [])

    def test_parse_empty_raises(self):
        """Empty string should raise ActionFailed."""
        from mac_maestro.keyboard import parse_hotkey

        with self.assertRaises(ActionFailed):
            parse_hotkey("")

    def test_parse_only_modifiers_raises(self):
        """Only modifiers without a key should raise ActionFailed."""
        from mac_maestro.keyboard import parse_hotkey

        with self.assertRaises(ActionFailed):
            parse_hotkey("cmd+shift")

    def test_parse_unknown_key_raises(self):
        """Unknown key should raise ActionFailed."""
        from mac_maestro.keyboard import parse_hotkey

        with self.assertRaises(ActionFailed):
            parse_hotkey("cmd+unicorn")

    def test_modifier_map_coverage(self):
        """All common modifier aliases should be in the map."""
        from mac_maestro.keyboard import MODIFIER_MAP

        for alias in ["cmd", "command", "shift", "alt", "option", "opt", "ctrl", "control"]:
            self.assertIn(alias, MODIFIER_MAP)


# ═══════════════════════════════════════════════════════════════════
# NEW: CGEvent Extensions Tests
# ═══════════════════════════════════════════════════════════════════


class TestCGEventExtensions(unittest.TestCase):
    """Tests that new CGEvent functions exist and are callable."""

    def test_right_click_at_is_callable(self):
        from mac_maestro.cgevents import right_click_at

        self.assertTrue(callable(right_click_at))

    def test_double_click_at_is_callable(self):
        from mac_maestro.cgevents import double_click_at

        self.assertTrue(callable(double_click_at))

    def test_functions_raise_without_quartz(self):
        """Without Quartz, functions should raise ActionFailed."""
        from mac_maestro import cgevents

        original = cgevents.QUARTZ_AVAILABLE
        try:
            cgevents.QUARTZ_AVAILABLE = False
            with self.assertRaises(ActionFailed):
                cgevents.right_click_at(0, 0)
            with self.assertRaises(ActionFailed):
                cgevents.double_click_at(0, 0)
        finally:
            cgevents.QUARTZ_AVAILABLE = original


# ═══════════════════════════════════════════════════════════════════
# NEW: Async Workflow Tests
# ═══════════════════════════════════════════════════════════════════


class TestAsyncWorkflow(unittest.TestCase):
    """Tests for async workflow methods."""

    def test_async_methods_exist(self):
        """Workflow should have async variants."""
        wf = MacMaestroWorkflow(bundle_id="com.test.app")
        self.assertTrue(hasattr(wf, "execute_action_async"))
        self.assertTrue(hasattr(wf, "run_sequence_async"))
        import inspect

        self.assertTrue(inspect.iscoroutinefunction(wf.execute_action_async))
        self.assertTrue(inspect.iscoroutinefunction(wf.run_sequence_async))

    def test_async_backoff_sleep_exists(self):
        """Module should export async backoff."""
        import inspect

        from mac_maestro.workflow import _async_backoff_sleep

        self.assertTrue(inspect.iscoroutinefunction(_async_backoff_sleep))


# ═══════════════════════════════════════════════════════════════════
# NEW: Trace File Persistence Tests
# ═══════════════════════════════════════════════════════════════════


class TestTraceFilePersistence(unittest.TestCase):
    """Tests for JSON Lines file trace persistence."""

    def setUp(self):
        import tempfile

        self.tmpdir = tempfile.mkdtemp()
        self.trace_file = os.path.join(self.tmpdir, "test_traces.jsonl")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_trace_to_file(self):
        """_write_trace_to_file should append a JSON line."""
        import json
        from pathlib import Path

        from mac_maestro.trace import _write_trace_to_file

        trace_file = Path(self.trace_file)

        # Temporarily override TRACE_FILE
        import mac_maestro.trace as trace_mod

        original = trace_mod.TRACE_FILE
        trace_mod.TRACE_FILE = trace_file

        try:
            _write_trace_to_file({"action": "click", "target": "Save"})

            self.assertTrue(trace_file.exists())
            with trace_file.open() as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)
            data = json.loads(lines[0])
            self.assertEqual(data["action"], "click")
        finally:
            trace_mod.TRACE_FILE = original

    def test_load_traces(self):
        """load_traces should return traces from a JSONL file."""
        import json

        from mac_maestro.trace import load_traces

        # Write test data
        with open(self.trace_file, "w") as f:
            f.write(json.dumps({"id": 1, "action": "click"}) + "\n")
            f.write(json.dumps({"id": 2, "action": "type"}) + "\n")
            f.write(json.dumps({"id": 3, "action": "hotkey"}) + "\n")

        traces = load_traces(self.trace_file, limit=10)

        self.assertEqual(len(traces), 3)
        # Most recent first
        self.assertEqual(traces[0]["id"], 3)
        self.assertEqual(traces[2]["id"], 1)

    def test_load_traces_with_limit(self):
        """load_traces should respect the limit parameter."""
        import json

        from mac_maestro.trace import load_traces

        with open(self.trace_file, "w") as f:
            for i in range(10):
                f.write(json.dumps({"id": i}) + "\n")

        traces = load_traces(self.trace_file, limit=3)
        self.assertEqual(len(traces), 3)

    def test_load_traces_empty_file(self):
        """load_traces should return empty list for nonexistent file."""
        from mac_maestro.trace import load_traces

        traces = load_traces("/nonexistent/path.jsonl")
        self.assertEqual(traces, [])

    def test_trace_append_only(self):
        """Multiple writes should create multiple lines."""
        from pathlib import Path

        import mac_maestro.trace as trace_mod
        from mac_maestro.trace import _write_trace_to_file

        trace_file = Path(self.trace_file)
        original = trace_mod.TRACE_FILE
        trace_mod.TRACE_FILE = trace_file

        try:
            _write_trace_to_file({"id": 1})
            _write_trace_to_file({"id": 2})

            with trace_file.open() as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 2)
        finally:
            trace_mod.TRACE_FILE = original


if __name__ == "__main__":
    unittest.main()
