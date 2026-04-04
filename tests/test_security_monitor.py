"""Tests for SecurityMonitorClassifier — V9 Hardening.

Covers:
  - IntentClassifier (7 Axioms)
  - ZeroTrustToolFilter
  - StochasticSandbox
"""

import os
import shutil
import sys
import unittest

sys.path.insert(
    0, "/Users/borjafernandezangulo/Cortex-Persist"
)

from cortex.extensions.security.security_monitor import (
    IntentClassifier,
    IntentVerdict,
    ParameterProvenance,
    ReversibilityTier,
    SecurityMonitorClassifier,
    ToolDataTag,
    ZeroTrustToolFilter,
)
from cortex.extensions.security.stochastic_sandbox import (
    StochasticSandbox,
)


class TestIntentClassifier(unittest.TestCase):
    """Tests for the 7 Intent Axioms."""

    def setUp(self):
        self.clf = IntentClassifier()
        IntentClassifier.clear_constraints()

    # --- R0: Read-only commands always pass ---

    def test_read_command_allowed(self):
        task = {"command": "cat README.md", "agent": "s1"}
        v = self.clf.classify(task, "show me the readme")
        self.assertTrue(v.allowed)
        self.assertEqual(v.tier, ReversibilityTier.R0_READ)

    def test_grep_command_allowed(self):
        task = {
            "command": "grep -rn 'TODO' ./src",
            "agent": "s2",
        }
        v = self.clf.classify(task, "find all TODOs")
        self.assertTrue(v.allowed)

    # --- Ω5: Questions Are NOT Consent ---

    def test_question_blocks_remote_mutation(self):
        task = {
            "command": "git push origin main",
            "agent": "s3",
        }
        v = self.clf.classify(task, "can we push this?")
        self.assertFalse(v.allowed)
        self.assertEqual(
            v.axiom_violated, "Ω5_QUESTION_NOT_CONSENT"
        )

    def test_question_allows_read(self):
        task = {"command": "ls -la", "agent": "s4"}
        v = self.clf.classify(task, "what files are here?")
        self.assertTrue(v.allowed)

    def test_spanish_question_detected(self):
        task = {
            "command": "forge script --broadcast",
            "agent": "s5",
        }
        v = self.clf.classify(
            task, "¿podemos deployar esto?"
        )
        self.assertFalse(v.allowed)
        self.assertEqual(
            v.axiom_violated, "Ω5_QUESTION_NOT_CONSENT"
        )

    # --- Ω2: Scope Escalation ---

    def test_mass_delete_blocked(self):
        task = {
            "command": "rm -rf /Users/borja/project",
            "agent": "cleaner",
        }
        v = self.clf.classify(task, "audit the code")
        self.assertFalse(v.allowed)
        self.assertEqual(
            v.axiom_violated, "Ω2_SCOPE_ESCALATION"
        )

    def test_git_clean_fdx_blocked(self):
        task = {
            "command": "git clean -fdx",
            "agent": "tidier",
        }
        v = self.clf.classify(task, "run the tests")
        self.assertFalse(v.allowed)
        self.assertEqual(
            v.axiom_violated, "Ω2_SCOPE_ESCALATION"
        )

    def test_db_drop_blocked(self):
        task = {
            "command": "psql -c 'DROP DATABASE prod'",
            "agent": "db-agent",
        }
        v = self.clf.classify(task, "check db status")
        self.assertFalse(v.allowed)

    # --- Ω4: Agent-Inferred Nullification ---

    def test_agent_inferred_r3_blocked(self):
        task = {
            "command": "rm -rf ./old_module",
            "agent": "optimizer",
        }
        v = self.clf.classify(
            task,
            "optimize the codebase",
            provenance=ParameterProvenance.AGENT_INFERRED,
        )
        self.assertFalse(v.allowed)

    # --- Ω3: High-Severity Precision ---

    def test_r4_requires_user_explicit(self):
        task = {
            "command": "git push origin main",
            "agent": "deployer",
        }
        # Agent-inferred provenance
        v = self.clf.classify(
            task,
            "deploy to production",
            provenance=ParameterProvenance.AGENT_INFERRED,
        )
        self.assertFalse(v.allowed)

        # User-explicit provenance
        v2 = self.clf.classify(
            task,
            "deploy to production",
            provenance=ParameterProvenance.USER_EXPLICIT,
        )
        self.assertTrue(v2.allowed)

    # --- Ω7: Boundary Persistence ---

    def test_persistent_constraint_enforced(self):
        IntentClassifier.add_constraint("git push")
        task = {
            "command": "git push origin dev",
            "agent": "deployer",
        }
        v = self.clf.classify(
            task,
            "push to dev",
            provenance=ParameterProvenance.USER_EXPLICIT,
        )
        self.assertFalse(v.allowed)
        self.assertEqual(
            v.axiom_violated, "Ω7_BOUNDARY_PERSISTENCE"
        )

    # --- Tier Classification ---

    def test_forge_broadcast_is_r4(self):
        task = {
            "command": "forge script Deploy --broadcast",
            "agent": "s",
        }
        v = self.clf.classify(
            task,
            "deploy contract",
            provenance=ParameterProvenance.USER_EXPLICIT,
        )
        self.assertEqual(v.tier, ReversibilityTier.R4_CRITICAL)

    def test_forge_build_is_r1(self):
        task = {
            "command": "forge build",
            "agent": "builder",
        }
        v = self.clf.classify(task, "build the project")
        self.assertEqual(
            v.tier, ReversibilityTier.R1_LOCAL_WRITE
        )
        self.assertTrue(v.allowed)

    def test_empty_command_blocked(self):
        task = {"command": "", "agent": "empty"}
        v = self.clf.classify(task, "do something")
        self.assertFalse(v.allowed)


class TestZeroTrustToolFilter(unittest.TestCase):
    """Tests for Ω6: Zero-Trust Tooling."""

    def setUp(self):
        self.filter = ZeroTrustToolFilter()

    def test_no_tool_outputs_allowed(self):
        task = {
            "command": "forge test --fuzz",
            "agent": "fuzzer",
        }
        v = self.filter.sanitize(task, tool_outputs=None)
        self.assertTrue(v.allowed)

    def test_tool_derived_destructive_blocked(self):
        task = {
            "command": "git push origin main",
            "agent": "deployer",
        }
        outputs = {
            "branch": ToolDataTag(
                source_tool="github_mcp",
                is_trusted=False,
            ),
        }
        v = self.filter.sanitize(task, tool_outputs=outputs)
        self.assertFalse(v.allowed)
        self.assertEqual(
            v.axiom_violated, "Ω6_ZERO_TRUST_TOOLING"
        )

    def test_tool_derived_read_allowed(self):
        task = {
            "command": "cat some_file.sol",
            "agent": "reader",
        }
        outputs = {
            "path": ToolDataTag(
                source_tool="github_mcp",
                is_trusted=False,
            ),
        }
        v = self.filter.sanitize(task, tool_outputs=outputs)
        self.assertTrue(v.allowed)


class TestSecurityMonitorClassifier(unittest.TestCase):
    """Integration tests for the full pipeline."""

    def setUp(self):
        self.monitor = SecurityMonitorClassifier()
        IntentClassifier.clear_constraints()

    def test_safe_read_passes_full_pipeline(self):
        task = {
            "command": "slither ./src",
            "agent": "auditor",
        }
        v = self.monitor.classify(
            task, user_request="audit the contracts"
        )
        self.assertTrue(v.allowed)

    def test_question_plus_destructive_blocked(self):
        task = {
            "command": "forge script --broadcast",
            "agent": "deployer",
        }
        v = self.monitor.classify(
            task, user_request="should we deploy?"
        )
        self.assertFalse(v.allowed)


class TestStochasticSandbox(unittest.TestCase):
    """Tests for the Stochastic Sandbox."""

    def setUp(self):
        self.sandbox = StochasticSandbox()
        self.test_dir = "/tmp/cortex_sandbox_test_src"
        os.makedirs(self.test_dir, exist_ok=True)
        # Create a dummy file
        with open(
            os.path.join(self.test_dir, "test.sol"), "w"
        ) as f:
            f.write("// SPDX")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        self.sandbox.cleanup_all()

    def test_fuzz_command_redirected(self):
        result = self.sandbox.intercept(
            "forge test --fuzz-runs 50000",
            cwd=self.test_dir,
        )
        self.assertTrue(result.is_redirected)
        self.assertEqual(result.matched_pattern, "FORGE_FUZZ")
        self.assertTrue(
            result.arena_path.startswith("/tmp/cortex_sandbox_")
        )

    def test_non_stochastic_passthrough(self):
        result = self.sandbox.intercept(
            "cat README.md", cwd=self.test_dir
        )
        self.assertFalse(result.is_redirected)

    def test_git_clean_redirected(self):
        result = self.sandbox.intercept(
            "git clean -fdx", cwd=self.test_dir
        )
        self.assertTrue(result.is_redirected)
        self.assertEqual(
            result.matched_pattern, "GIT_CLEAN_FORCE"
        )

    def test_arena_cleanup(self):
        result = self.sandbox.intercept(
            "forge test --fuzz-runs 1000",
            cwd=self.test_dir,
        )
        self.assertTrue(
            os.path.exists(result.arena_path)
        )
        self.sandbox.cleanup(result.arena_path)
        self.assertFalse(
            os.path.exists(result.arena_path)
        )

    def test_cleanup_refuses_outside_arena(self):
        ok = self.sandbox.cleanup("/Users/borja/important")
        self.assertFalse(ok)

    def test_list_active_arenas(self):
        self.sandbox.intercept(
            "forge test --fuzz", cwd=self.test_dir
        )
        arenas = self.sandbox.list_active_arenas()
        self.assertGreaterEqual(len(arenas), 1)


class TestGuardRuntimeIntegration(unittest.TestCase):
    """Tests for IntentGuardWrapper + enforce_guard_pipeline."""

    def setUp(self):
        IntentClassifier.clear_constraints()

    def test_intent_guard_wrapper_blocks_scope_creep(self):
        from cortex.extensions.security.guard_runtime import (
            IntentGuardWrapper,
        )
        guard = IntentGuardWrapper()
        context = {
            "command": "rm -rf /Users/borja/project",
            "agent": "cleaner",
            "user_request": "audit the code",
        }
        outcome = guard.evaluate(context)
        self.assertFalse(outcome.allowed)
        self.assertIn("intent.", outcome.code)

    def test_intent_guard_wrapper_allows_read(self):
        from cortex.extensions.security.guard_runtime import (
            IntentGuardWrapper,
        )
        guard = IntentGuardWrapper()
        context = {
            "command": "cat README.md",
            "agent": "reader",
            "user_request": "show the readme",
        }
        outcome = guard.evaluate(context)
        self.assertTrue(outcome.allowed)
        self.assertEqual(outcome.code, "intent.allowed")

    def test_intent_guard_no_command_skips(self):
        from cortex.extensions.security.guard_runtime import (
            IntentGuardWrapper,
        )
        guard = IntentGuardWrapper()
        context = {"content": "some text"}
        outcome = guard.evaluate(context)
        self.assertTrue(outcome.allowed)
        self.assertEqual(
            outcome.code, "intent.no_command"
        )

    def test_default_pipeline_exists(self):
        from cortex.extensions.security.guard_runtime import (
            DEFAULT_GUARD_PIPELINE,
        )
        self.assertGreaterEqual(
            len(DEFAULT_GUARD_PIPELINE), 6
        )
        names = [g.name for g in DEFAULT_GUARD_PIPELINE]
        self.assertIn("intent_guard", names)
        self.assertIn("injection_guard", names)
        # Intent guard should be first
        self.assertEqual(names[0], "intent_guard")

    def test_pipeline_blocks_destructive(self):
        from cortex.extensions.security.guard_runtime import (
            IntentGuardWrapper,
            enforce_guard_pipeline,
        )
        guards = [IntentGuardWrapper()]
        context = {
            "command": "rm -rf /",
            "agent": "destroyer",
            "user_request": "clean things",
            "content": "rm -rf /",
        }
        with self.assertRaises(ValueError) as cm:
            enforce_guard_pipeline(guards, context)
        self.assertIn("SECURITY GUARD BLOCK", str(cm.exception))

    def test_pipeline_allows_safe(self):
        from cortex.extensions.security.guard_runtime import (
            IntentGuardWrapper,
            enforce_guard_pipeline,
        )
        guards = [IntentGuardWrapper()]
        context = {
            "command": "ls -la",
            "agent": "lister",
            "user_request": "list files",
            "content": "ls -la",
        }
        outcomes = enforce_guard_pipeline(
            guards, context
        )
        self.assertTrue(all(o.allowed for o in outcomes))


if __name__ == "__main__":
    unittest.main()
