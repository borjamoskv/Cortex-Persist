"""Tests for Mac-Maestro-Ω V5: Full Master Protocol verification."""

from __future__ import annotations

import os
import sys
import time
import unittest
from unittest.mock import patch

_SDK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SDK_ROOT not in sys.path:
    sys.path.insert(0, _SDK_ROOT)

from mac_maestro.models import (  # noqa: E402
    ActionFailed, AXNodeSnapshot, ElementMatch,
    ResolvedTarget, UIAction,
)
from mac_maestro.workflow import MacMaestroWorkflow, _backoff_sleep  # noqa: E402
from mac_maestro.applescript import sanitize_applescript_string  # noqa: E402
from mac_maestro.resolver import resolve  # noqa: E402
from mac_maestro.matcher import find_elements, find_best  # noqa: E402
from mac_maestro.trace import emit_trace  # noqa: E402


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _make_snapshot(**kwargs) -> AXNodeSnapshot:
    """Build an AXNodeSnapshot with sensible defaults."""
    defaults = dict(
        role=None, subrole=None, title=None, value=None,
        identifier=None, description=None, enabled=True, focused=False,
        position=None, size=None, path=(), children=[],
    )
    defaults.update(kwargs)
    return AXNodeSnapshot(**defaults)


def _make_tree() -> AXNodeSnapshot:
    """Build a realistic AX tree for testing."""
    return _make_snapshot(
        role="AXApplication", title="TestApp", path=(0,),
        children=[
            _make_snapshot(
                role="AXWindow", title="Main Window", path=(0, 0),
                position=(0.0, 0.0), size=(800.0, 600.0),
                children=[
                    _make_snapshot(
                        role="AXButton", title="Save",
                        identifier="save-btn",
                        position=(100.0, 50.0), size=(80.0, 30.0),
                        path=(0, 0, 0),
                    ),
                    _make_snapshot(
                        role="AXButton", title="Cancel",
                        position=(200.0, 50.0), size=(80.0, 30.0),
                        path=(0, 0, 1),
                    ),
                    _make_snapshot(
                        role="AXTextField", title="Search",
                        description="Search field",
                        value="",
                        position=(300.0, 100.0), size=(200.0, 24.0),
                        path=(0, 0, 2),
                    ),
                    _make_snapshot(
                        role="AXCheckBox", title="Remember me",
                        value="0", enabled=False,
                        position=(100.0, 150.0), size=(120.0, 20.0),
                        path=(0, 0, 3),
                    ),
                    _make_snapshot(
                        role="AXMenuItem", title="Export as PDF",
                        description="Export the document",
                        position=(50.0, 200.0), size=(150.0, 22.0),
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

    @patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_primary_success(self, mock_tl):
        wf = self._make_workflow()
        executed = []
        action = UIAction(
            name="click", vector="B",
            executor=lambda: executed.append("primary"),
        )
        result = wf.execute_action(action, apply_safety_gate=False)
        self.assertTrue(result)
        self.assertEqual(executed, ["primary"])

    @patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_fallback_on_failure(self, mock_tl):
        wf = self._make_workflow()
        executed = []

        def fail():
            executed.append("fail")
            raise RuntimeError("AX unavailable")

        action = UIAction(
            name="click", vector="B", executor=fail,
            fallbacks=[UIAction(name="click_cg", vector="D",
                                executor=lambda: executed.append("fallback"))],
        )
        result = wf.execute_action(action, apply_safety_gate=False)
        self.assertTrue(result)
        self.assertEqual(executed, ["fail", "fallback"])

    @patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_all_fallbacks_exhausted(self, mock_tl):
        wf = self._make_workflow()

        def fail():
            raise RuntimeError("always fails")

        action = UIAction(
            name="click", vector="B", executor=fail,
            fallbacks=[
                UIAction(name="click_cg", vector="D", executor=fail),
            ],
        )
        with self.assertRaises(ActionFailed):
            wf.execute_action(action, apply_safety_gate=False)

    @patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_postcondition_failure_not_swallowed(self, mock_tl):
        wf = self._make_workflow()
        action = UIAction(
            name="type_text", vector="C",
            executor=lambda: None,
            postconditions=[lambda: False],
            idempotent=False,
        )
        with self.assertRaises(ActionFailed) as ctx:
            wf.execute_action(action, apply_safety_gate=False)
        self.assertIn("Postconditions failed", str(ctx.exception))

    @patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_safety_gate_blocks_unsafe(self, mock_tl):
        wf = self._make_workflow()
        action = UIAction(
            name="delete", vector="A",
            executor=lambda: None, unsafe=False,
        )
        with self.assertRaises(PermissionError):
            wf.execute_action(action, apply_safety_gate=True)

    @patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
    def test_precondition_failure(self, mock_tl):
        wf = self._make_workflow()
        action = UIAction(
            name="click", vector="B",
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
            name="run_as", vector="A",
            target_query={"script": 'tell app "Finder" to activate'},
        )
        executor = resolve(action)
        self.assertTrue(callable(executor))

    def test_resolve_applescript_app_name(self):
        action = UIAction(
            name="open_app", vector="A",
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
            pid=1234, app_name="Test", bundle_id="com.test",
            window_title="Main", element=None,
            position=(140.0, 65.0),
            resolution_method="ax_semantic", degraded=False,
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
    @patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
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

    @patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
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

    @patch("mac_maestro.workflow.MacMaestroWorkflow._target_lock")
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
            actions, apply_safety_gate=False, abort_on_failure=False,
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
        results = find_elements(self.tree, description="Search field")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].role, "AXTextField")

    def test_find_by_identifier(self):
        results = find_elements(self.tree, identifier="save-btn")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Save")

    def test_fuzzy_substring_match(self):
        results = find_elements(self.tree, title="Export")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].role, "AXMenuItem")

    def test_fuzzy_case_insensitive(self):
        results = find_elements(self.tree, title="save")
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
            run_id="test-run", bundle_id="com.test",
            pid=None, frontmost=False, window_title=None,
            selected_vector="A", outcome="success",
            target_query={},
        )
        self.assertTrue(trace["degraded"])

    def test_trace_not_degraded_with_pid(self):
        trace = emit_trace(
            run_id="test-run", bundle_id="com.test",
            pid=12345, frontmost=True, window_title="Main",
            selected_vector="B", outcome="success",
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
            run_id="test-run", bundle_id="com.test",
            pid=1, frontmost=True, window_title="Win",
            selected_vector="B", outcome="success",
            target_query={}, resolution_method=None,
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
            pid=1, app_name="A", bundle_id="com.a",
            window_title=None, element=None, position=None,
            resolution_method="manual", degraded=True,
        )
        self.assertTrue(rt.degraded)

    def test_not_degraded(self):
        rt = ResolvedTarget(
            pid=1, app_name="A", bundle_id="com.a",
            window_title="Win", element=None, position=(100, 50),
            resolution_method="ax_semantic", degraded=False,
            confidence=0.9,
        )
        self.assertFalse(rt.degraded)
        self.assertEqual(rt.confidence, 0.9)


class TestElementMatchCenter(unittest.TestCase):
    def test_center_calculation(self):
        em = ElementMatch(
            ref=None, role="AXButton", subrole=None,
            title="OK", value=None, identifier=None, description=None,
            position=(100.0, 200.0), size=(60.0, 30.0),
            score=0.8, reasons=["role=AXButton"],
        )
        self.assertEqual(em.center, (130.0, 215.0))

    def test_center_none_without_position(self):
        em = ElementMatch(
            ref=None, role="AXButton", subrole=None,
            title="OK", value=None, identifier=None, description=None,
            position=None, size=None,
            score=0.5, reasons=[],
        )
        self.assertIsNone(em.center)


if __name__ == "__main__":
    unittest.main()
