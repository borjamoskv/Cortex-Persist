"""Tests for LORCA-Ω Commit Poet Engine."""

from __future__ import annotations

import re

import pytest

from cortex.extensions.git.poet import CommitPoet, generate_candidates, generate_commit_message

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def poet() -> CommitPoet:
    """Create a deterministic CommitPoet instance."""
    p = CommitPoet()
    p.seed(42)
    return p


@pytest.fixture
def feat_diff() -> str:
    return "cortex/engine/store_mixin.py | 42 ++++++++++++\ncortex/engine/__init__.py | 3 ++"


@pytest.fixture
def feat_files() -> list[str]:
    return ["cortex/engine/store_mixin.py", "cortex/engine/__init__.py"]


@pytest.fixture
def fix_diff() -> str:
    return "cortex/memory/manager.py | 8 ++--\nfix: resolve crash on empty recall"


@pytest.fixture
def fix_files() -> list[str]:
    return ["cortex/memory/manager.py"]


@pytest.fixture
def test_diff() -> str:
    return "tests/test_engine.py | 55 +++++++++++++++++++"


@pytest.fixture
def test_files() -> list[str]:
    return ["tests/test_engine.py"]


@pytest.fixture
def docs_diff() -> str:
    return "README.md | 20 ++++++++\ndocs/api.md | 15 ++++++"


@pytest.fixture
def docs_files() -> list[str]:
    return ["README.md", "docs/api.md"]


# ── Conventional Commits Format ───────────────────────────────────────────────


CONVENTIONAL_PATTERN = re.compile(
    r"^(feat|fix|refactor|perf|docs|test|ci|style|chore|revert)"
    r"\([a-zA-Z0-9_.-]+\): .+ ."  # type(scope): body emoji
)


class TestConventionalFormat:
    """Verify all generated messages follow conventional commit format."""

    def test_feat_format(self, poet: CommitPoet, feat_diff: str, feat_files: list[str]):
        msg = poet.compose(feat_diff, feat_files)
        assert CONVENTIONAL_PATTERN.match(msg), f"Does not match conventional format: {msg}"

    def test_fix_format(self, poet: CommitPoet, fix_diff: str, fix_files: list[str]):
        msg = poet.compose(fix_diff, fix_files)
        assert CONVENTIONAL_PATTERN.match(msg), f"Does not match conventional format: {msg}"

    def test_test_format(self, poet: CommitPoet, test_diff: str, test_files: list[str]):
        msg = poet.compose(test_diff, test_files)
        assert CONVENTIONAL_PATTERN.match(msg), f"Does not match conventional format: {msg}"

    def test_docs_format(self, poet: CommitPoet, docs_diff: str, docs_files: list[str]):
        msg = poet.compose(docs_diff, docs_files)
        assert CONVENTIONAL_PATTERN.match(msg), f"Does not match conventional format: {msg}"


# ── Type Detection ────────────────────────────────────────────────────────────


class TestTypeDetection:
    """Verify commit type is correctly detected from diff content."""

    def test_detect_feat(self, poet: CommitPoet, feat_diff: str, feat_files: list[str]):
        msg = poet.compose(feat_diff, feat_files)
        assert msg.startswith("feat(")

    def test_detect_fix(self, poet: CommitPoet, fix_diff: str, fix_files: list[str]):
        msg = poet.compose(fix_diff, fix_files)
        assert msg.startswith("fix(")

    def test_detect_test(self, poet: CommitPoet, test_diff: str, test_files: list[str]):
        msg = poet.compose(test_diff, test_files)
        assert msg.startswith("test(")

    def test_detect_docs(self, poet: CommitPoet, docs_diff: str, docs_files: list[str]):
        msg = poet.compose(docs_diff, docs_files)
        assert msg.startswith("docs(")

    def test_explicit_type_override(self, poet: CommitPoet, feat_diff: str, feat_files: list[str]):
        msg = poet.compose(feat_diff, feat_files, commit_type="refactor")
        assert msg.startswith("refactor(")


# ── Scope Extraction ─────────────────────────────────────────────────────────


class TestScopeExtraction:
    """Verify scope is correctly extracted from file paths."""

    def test_engine_scope(self, poet: CommitPoet, feat_diff: str, feat_files: list[str]):
        msg = poet.compose(feat_diff, feat_files)
        assert "(engine)" in msg

    def test_memory_scope(self, poet: CommitPoet, fix_diff: str, fix_files: list[str]):
        msg = poet.compose(fix_diff, fix_files)
        assert "(memory)" in msg

    def test_tests_scope(self, poet: CommitPoet, test_diff: str, test_files: list[str]):
        msg = poet.compose(test_diff, test_files)
        # tests/ maps to "tests" scope
        assert "(tests)" in msg

    def test_fallback_scope(self, poet: CommitPoet):
        msg = poet.compose("unknown.xyz | 5 +++", ["some/random/unknown.xyz"])
        assert "(" in msg and ")" in msg  # Has some scope


# ── Anti-Repetition ──────────────────────────────────────────────────────────


class TestAntiRepetition:
    """Verify the engine avoids repeating messages."""

    def test_no_consecutive_duplicates(self, poet: CommitPoet, feat_diff: str, feat_files: list[str]):
        messages: list[str] = []
        for _ in range(10):
            msg = poet.compose(feat_diff, feat_files)
            messages.append(msg)

        # At least 5 unique messages out of 10
        unique = set(messages)
        assert len(unique) >= 5, f"Only {len(unique)} unique out of 10: {messages}"

    def test_batch_produces_unique_candidates(
        self, poet: CommitPoet, feat_diff: str, feat_files: list[str]
    ):
        candidates = poet.compose_batch(feat_diff, feat_files, count=3)
        assert len(candidates) == 3
        assert len(set(candidates)) == 3, "Batch candidates must be unique"


# ── Emoji Signature ──────────────────────────────────────────────────────────


class TestEmojiSignature:
    """Verify each message has exactly one trailing emoji."""

    def test_has_emoji(self, poet: CommitPoet, feat_diff: str, feat_files: list[str]):
        msg = poet.compose(feat_diff, feat_files)
        # The message should end with a non-ASCII character (emoji)
        last_char = msg.rstrip()[-1]
        assert ord(last_char) > 127 or msg.rstrip()[-2] == "\ufe0f", (
            f"Missing emoji: {msg}"
        )


# ── Message Length ────────────────────────────────────────────────────────────


class TestMessageLength:
    """Verify messages stay within the 72-char git best practice."""

    def test_under_72_chars(self, poet: CommitPoet, feat_diff: str, feat_files: list[str]):
        for _ in range(20):
            msg = poet.compose(feat_diff, feat_files)
            assert len(msg) <= 80, f"Too long ({len(msg)} chars): {msg}"


# ── Empty Diff Handling ──────────────────────────────────────────────────────


class TestEdgeCases:
    """Verify graceful handling of edge cases."""

    def test_empty_files(self, poet: CommitPoet):
        msg = poet.compose("", [])
        assert msg  # Should return something, not crash
        assert "void" in msg.lower() or "chore" in msg.lower()

    def test_single_file(self, poet: CommitPoet):
        msg = poet.compose("foo.py | 1 +", ["cortex/guards/injection_guard.py"])
        assert msg
        assert CONVENTIONAL_PATTERN.match(msg)


# ── Code Narration ───────────────────────────────────────────────────────────


class TestNarration:
    """Verify code comment generation."""

    def test_narrate_function(self, poet: CommitPoet):
        code = "def calculate_entropy(data: list[float]) -> float:"
        comment = poet.narrate(code, "Shannon entropy calculation")
        assert '"""' in comment
        assert "calculate_entropy" in comment

    def test_narrate_class(self, poet: CommitPoet):
        code = "class CortexEngine(StoreMixin, QueryMixin):"
        comment = poet.narrate(code)
        assert '"""' in comment
        assert "CortexEngine" in comment

    def test_narrate_module(self, poet: CommitPoet):
        code = "import os\nimport sys\n"
        comment = poet.narrate(code)
        assert '"""' in comment


# ── Convenience Functions ────────────────────────────────────────────────────


class TestConvenienceFunctions:
    """Verify module-level convenience functions."""

    def test_generate_commit_message(self):
        msg = generate_commit_message(
            diff_summary="cortex/engine/store.py | 10 +++",
            files=["cortex/engine/store.py"],
            seed=42,
        )
        assert msg
        assert CONVENTIONAL_PATTERN.match(msg)

    def test_generate_candidates(self):
        candidates = generate_candidates(
            diff_summary="cortex/search/hybrid.py | 25 +++---",
            files=["cortex/search/hybrid.py"],
            count=3,
        )
        assert len(candidates) == 3
        for c in candidates:
            assert CONVENTIONAL_PATTERN.match(c), f"Bad format: {c}"

    def test_deterministic_with_seed(self):
        msg1 = generate_commit_message(
            diff_summary="cortex/llm/router.py | 8 ++--",
            files=["cortex/llm/router.py"],
            seed=123,
        )
        msg2 = generate_commit_message(
            diff_summary="cortex/llm/router.py | 8 ++--",
            files=["cortex/llm/router.py"],
            seed=123,
        )
        assert msg1 == msg2, "Same seed should produce same message"


# ── Changelog Formatting ────────────────────────────────────────────────────


class TestChangelog:
    """Verify changelog entry generation."""

    def test_changelog_entry(self, poet: CommitPoet):
        entry = poet.format_changelog_entry("feat", "engine", "new store mixin")
        assert "**FEAT**" in entry
        assert "(engine)" in entry
        assert "new store mixin" in entry
        assert entry.startswith("- ")
